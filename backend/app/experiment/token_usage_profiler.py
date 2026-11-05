import csv
import hashlib
import json
import statistics
import uuid
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path


# USD per 1M tokens; standard model rates verified against the official API
# pricing pages on 2026-11-05.
MODEL_PRICING = {
    "gpt-3.5-turbo": (0.50, 1.50),
    "gpt-3.5-turbo-0125": (0.50, 1.50),
    "gpt-3.5-turbo-1106": (1.00, 2.00),
    "gpt-3.5-turbo-16k": (3.00, 4.00),
    "gpt-3.5-turbo-16k-0613": (3.00, 4.00),
    "gpt-3.5-turbo-instruct": (1.50, 2.00),
    "gpt-3.5-turbo-instruct:20230824-v2": (1.50, 2.00),
    # Standard API USD per 1M tokens, from the official GPT-6 Luna model page.
    "gpt-6-luna": (0.10, 0.50),
}
# GPT-6 Luna Standard API USD per 1M tokens. The budget reservations use the
# highest applicable input rate (cache write) and the standard output rate.
MODEL_TOKEN_PRICING = {
    "gpt-6-luna": {
        "input": 0.10,
        "cached_input": 0.01,
        "cache_write": 0.125,
        "output": 0.50,
    }
}
DEFAULT_COST_PROFILE_PATH = (
    Path(__file__).resolve().parents[3]
    / "verification_artifacts"
    / "research_cost_profile"
    / "cost_profile.json"
)


@dataclass
class ProviderCallUsage:
    purpose: str
    requested_model: str
    actual_model: str
    prompt_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    cache_write_usage_reported: bool
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    estimated_cost_usd: float


_ACTIVE_PROFILER = ContextVar("active_geo_cost_profiler", default=None)
_ACTIVE_OUTREACH_BUDGET = ContextVar("active_outreach_provider_budget", default=None)


class ProviderBudgetBlocked(RuntimeError):
    """The bounded one-job provider budget failed closed."""


class OutreachProviderBudget:
    """Append-only provider budget ledger scoped to one durable outreach job."""

    MAX_CUMULATIVE_COST_USD = Decimal("5.00")
    MAX_MODEL_CALLS = 5
    MAX_INPUT_BYTES_PER_CALL = 48000
    MAX_INPUT_TOKENS_PER_CALL = MAX_INPUT_BYTES_PER_CALL
    MAX_OUTPUT_TOKENS_PER_CALL = 1024
    # Exa Auto Search is $7/1k requests; this path caps results at five (below
    # the first ten-result tier, so no additional-result charge applies).
    SEARCH_COST_USD = {"exa": 0.007}

    def __init__(self, durable_store, job_key: str):
        self.store = durable_store
        self.job_key = job_key
        # A fresh identity for each durable advance attempt. It is stored with
        # every response before control returns to parsing code.
        self.attempt_id = str(uuid.uuid4())
        self.last_response_sequence = None
        self.experiment_id = None
        self.replayed_response_ids = set()
        self._token = None
        self.reservations = []
        self.settlements = {}
        self.search_reserved = False
        self.search_settled = False
        self._load_ledger()

    @staticmethod
    def _decimal(value, description: str) -> Decimal:
        try:
            amount = Decimal(str(value))
        except Exception as exc:
            raise ProviderBudgetBlocked(f"Invalid provider ledger amount for {description}") from exc
        if not amount.is_finite() or amount < 0:
            raise ProviderBudgetBlocked(f"Invalid provider ledger amount for {description}")
        return amount

    @staticmethod
    def _field(value, *names):
        for name in names:
            if isinstance(value, dict) and name in value:
                return value[name]
            found = getattr(value, name, None)
            if found is not None:
                return found
        return None

    @classmethod
    def _usage_cost(cls, usage, prompt_tokens: int, completion_tokens: int):
        """Return conservative billed cost and auditable cache token breakdown.

        OpenAI Chat Completions reports cache reads, but not all API versions
        expose cache-write counts. When that count is absent, charge every
        non-cached input token at the higher cache-write rate for cap accounting.
        """
        pricing = MODEL_TOKEN_PRICING["gpt-6-luna"]
        details = cls._field(usage, "prompt_tokens_details", "input_tokens_details")
        cached_value = cls._field(details, "cached_tokens", "cached_input_tokens")
        if cached_value is None:
            cached_value = 0
        cached = int(cached_value or 0)
        write_value = cls._field(
            details,
            "cache_write_tokens",
            "cache_creation_tokens",
            "cache_creation_input_tokens",
        )
        if write_value is None:
            write_value = cls._field(
                usage,
                "cache_write_tokens",
                "cache_creation_tokens",
                "cache_creation_input_tokens",
            )
        write_reported = write_value is not None
        writes = int(write_value or 0) if write_reported else max(0, prompt_tokens - cached)
        if cached < 0 or writes < 0 or cached + writes > prompt_tokens:
            raise ProviderBudgetBlocked("Provider cache usage is inconsistent with prompt token usage")
        standard = prompt_tokens - cached - writes
        cost = (
            Decimal(standard) * Decimal(str(pricing["input"]))
            + Decimal(cached) * Decimal(str(pricing["cached_input"]))
            + Decimal(writes) * Decimal(str(pricing["cache_write"]))
            + Decimal(completion_tokens) * Decimal(str(pricing["output"]))
        ) / Decimal(1_000_000)
        return cost, cached, writes, write_reported

    def _load_ledger(self):
        """Rebuild authoritative reservations/settlements; malformed state blocks spend."""
        records = [
            record for record in self.store.records("outreach_provider_budget")
            if record.get("job_key") == self.job_key
        ]
        model_reservations = {}
        model_settlements = {}
        search_reservations = []
        search_settlements = []
        for record in records:
            event = record.get("event")
            if event == "reserve_model":
                try:
                    sequence = int(record["sequence"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ProviderBudgetBlocked("Malformed model reservation in provider ledger") from exc
                if sequence in model_reservations:
                    raise ProviderBudgetBlocked("Duplicate model reservation in provider ledger")
                model_reservations[sequence] = record
            elif event == "settle_model":
                try:
                    sequence = int(record["sequence"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ProviderBudgetBlocked("Malformed model settlement in provider ledger") from exc
                if sequence in model_settlements:
                    raise ProviderBudgetBlocked("Duplicate model settlement in provider ledger")
                model_settlements[sequence] = record
            elif event == "reserve_search":
                search_reservations.append(record)
            elif event == "settle_search":
                search_settlements.append(record)

        if len(search_reservations) > 1 or len(search_settlements) > 1:
            raise ProviderBudgetBlocked("Duplicate search reservation or settlement in provider ledger")
        if search_settlements and not search_reservations:
            raise ProviderBudgetBlocked("Search settlement has no matching reservation")
        if search_reservations:
            reserved_search = search_reservations[0]
            if reserved_search.get("provider") != "exa":
                raise ProviderBudgetBlocked("Search reservation provider is outside the authorized budget")
            reserved_search_cost = self._decimal(
                reserved_search.get("worst_case_cost_usd"), "search reservation"
            )
            if search_settlements:
                settled_search = search_settlements[0]
                if settled_search.get("provider") != reserved_search.get("provider"):
                    raise ProviderBudgetBlocked("Search settlement does not match its reservation")
                if self._decimal(settled_search.get("actual_cost_usd"), "search settlement") > reserved_search_cost:
                    raise ProviderBudgetBlocked("Search settlement exceeds its reservation")
        if set(model_settlements) - set(model_reservations):
            raise ProviderBudgetBlocked("Model settlement has no matching reservation")
        if len(model_reservations) > self.MAX_MODEL_CALLS:
            raise ProviderBudgetBlocked("Provider ledger exceeds the five model-call allowance")
        for sequence, settlement in model_settlements.items():
            reservation = model_reservations[sequence]
            if settlement.get("model") != reservation.get("model"):
                raise ProviderBudgetBlocked("Model settlement does not match its reservation")
            settled_cost = self._decimal(settlement.get("actual_cost_usd"), "model settlement")
            reserved_cost = self._decimal(reservation.get("worst_case_cost_usd"), "model reservation")
            if settled_cost > reserved_cost:
                raise ProviderBudgetBlocked("Model settlement exceeds its reservation")
        self.reservations = [model_reservations[key] for key in sorted(model_reservations)]
        self.settlements = model_settlements
        self.search_reserved = bool(search_reservations)
        self.search_settled = bool(search_settlements)
        return records, model_reservations, model_settlements, search_reservations, search_settlements

    def __enter__(self):
        self._token = _ACTIVE_OUTREACH_BUDGET.set(self)
        return self

    def __exit__(self, *_):
        _ACTIVE_OUTREACH_BUDGET.reset(self._token)

    @property
    def committed_and_reserved_cost(self):
        _, reservations, settlements, search_reservations, search_settlements = self._load_ledger()
        total = Decimal("0")
        if search_reservations:
            if search_settlements:
                total += self._decimal(search_settlements[0].get("actual_cost_usd"), "search settlement")
            else:
                total += self._decimal(search_reservations[0].get("worst_case_cost_usd"), "search reservation")
        for sequence, reservation in reservations.items():
            settlement = settlements.get(sequence)
            if settlement is None:
                total += self._decimal(reservation.get("worst_case_cost_usd"), "model reservation")
                continue
            recorded = self._decimal(settlement.get("actual_cost_usd"), "model settlement")
            prompt = int(settlement.get("prompt_tokens", 0) or 0)
            completion = int(settlement.get("completion_tokens", 0) or 0)
            cached = int(settlement.get("cached_input_tokens", 0) or 0)
            write_value = settlement.get("cache_write_tokens")
            writes = int(write_value) if write_value is not None else max(0, prompt - cached)
            if cached < 0 or writes < 0 or cached + writes > prompt:
                raise ProviderBudgetBlocked("Persisted model cache usage is inconsistent")
            pricing = MODEL_TOKEN_PRICING["gpt-6-luna"]
            conservative = (
                Decimal(prompt - cached - writes) * Decimal(str(pricing["input"]))
                + Decimal(cached) * Decimal(str(pricing["cached_input"]))
                + Decimal(writes) * Decimal(str(pricing["cache_write"]))
                + Decimal(completion) * Decimal(str(pricing["output"]))
            ) / Decimal(1_000_000)
            total += max(recorded, conservative)
        return float(total)

    def _ensure_capacity(self, additional_cost: float):
        current = self._decimal(self.committed_and_reserved_cost, "cumulative budget")
        additional = self._decimal(additional_cost, "new reservation")
        if current + additional > self.MAX_CUMULATIVE_COST_USD:
            raise ProviderBudgetBlocked(
                f"The $5.00 combined Exa/OpenAI job budget would be exceeded "
                f"(settled and reserved: ${current:.6f}; requested reserve: ${additional:.6f})"
            )

    def reserve_search(self, provider_name: str):
        provider = provider_name.lower()
        if provider != "exa":
            raise ProviderBudgetBlocked("The single authorized job is restricted to one Exa search request")
        self._load_ledger()
        if self.search_reserved:
            raise ProviderBudgetBlocked("This durable job has already reserved its only search request")
        cost = self.SEARCH_COST_USD[provider]
        self._ensure_capacity(cost)
        self.store.append("outreach_provider_budget", {
            "record_id": f"outreach-budget:{self.job_key}:search", "event": "reserve_search",
            "job_key": self.job_key, "provider": provider, "max_results": 5,
            "worst_case_cost_usd": cost,
        })
        self.search_reserved = True

    def settle_search(self, provider_name: str, returned_documents: int):
        provider = provider_name.lower()
        self._load_ledger()
        if not self.search_reserved or self.search_settled or provider not in self.SEARCH_COST_USD:
            raise ProviderBudgetBlocked("Search usage cannot be settled against this job's reservation")
        if int(returned_documents) < 0 or int(returned_documents) > 5:
            raise ProviderBudgetBlocked("Search response exceeded the five-document reserved limit")
        self.store.append("outreach_provider_budget", {
            "record_id": f"outreach-budget:{self.job_key}:search:settle",
            "event": "settle_search", "job_key": self.job_key,
            "provider": provider, "returned_documents": int(returned_documents),
            "actual_cost_usd": self.SEARCH_COST_USD[provider],
        })
        self.search_settled = True

    def reserve_model(self, model: str, messages: list[dict], max_output_tokens: int) -> int:
        _, existing_reservations, existing_settlements, search_reservations, search_settlements = self._load_ledger()
        if model != "gpt-6-luna":
            raise ProviderBudgetBlocked("Outreach research is restricted to the bounded GPT-6 Luna model path")
        if search_reservations and not search_settlements:
            raise ProviderBudgetBlocked("An earlier search request has an unresolved billable outcome; reconciliation is required")
        if any(sequence not in existing_settlements for sequence in existing_reservations):
            raise ProviderBudgetBlocked("An earlier model request has an unresolved billable outcome; reconciliation is required")
        if len(existing_reservations) >= self.MAX_MODEL_CALLS:
            raise ProviderBudgetBlocked("The durable job has exhausted its five model-call allowance")
        if max_output_tokens < 1 or max_output_tokens > self.MAX_OUTPUT_TOKENS_PER_CALL:
            raise ProviderBudgetBlocked("Model output token cap exceeds the one-job budget")
        input_bytes = sum(len(str(message.get("content") or "").encode("utf-8")) for message in messages)
        if input_bytes > self.MAX_INPUT_BYTES_PER_CALL:
            raise ProviderBudgetBlocked("Model input exceeds the one-job token cap")
        pricing = MODEL_TOKEN_PRICING[model]
        worst = (
            self.MAX_INPUT_TOKENS_PER_CALL / 1_000_000 * max(pricing["input"], pricing["cache_write"])
            + max_output_tokens / 1_000_000 * pricing["output"]
        )
        self._ensure_capacity(worst)
        sequence = max(existing_reservations.keys() or [0]) + 1
        self.store.append("outreach_provider_budget", {
            "record_id": f"outreach-budget:{self.job_key}:model:{sequence}:reserve",
            "event": "reserve_model", "job_key": self.job_key, "sequence": sequence,
            "model": model, "input_token_limit": self.MAX_INPUT_TOKENS_PER_CALL,
            "output_token_limit": max_output_tokens, "worst_case_cost_usd": worst,
        })
        self.reservations.append({"sequence": sequence, "input_token_limit": self.MAX_INPUT_TOKENS_PER_CALL,
                                  "output_token_limit": max_output_tokens,
                                  "worst_case_cost_usd": worst})
        return sequence

    def settle_model(self, sequence: int, model: str, usage):
        if usage is None or (model not in MODEL_TOKEN_PRICING and not model.startswith("gpt-6-luna-")):
            raise ProviderBudgetBlocked("Provider usage or pricing is unavailable; reservation remains charged")
        _, reservations, settlements, _, _ = self._load_ledger()
        reservation = reservations.get(int(sequence))
        if reservation is None or int(sequence) in settlements:
            raise ProviderBudgetBlocked("Model usage cannot be settled against this job's reservation")
        if model != reservation.get("model") and not model.startswith("gpt-6-luna-"):
            raise ProviderBudgetBlocked("Actual model does not match the reserved model")
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        if prompt > int(reservation["input_token_limit"]) or completion > int(reservation["output_token_limit"]):
            raise ProviderBudgetBlocked("Actual provider usage exceeded its reserved token bound")
        cost, cached, writes, write_reported = self._usage_cost(usage, prompt, completion)
        reserved = self._decimal(reservation.get("worst_case_cost_usd"), "model reservation")
        if cost > reserved:
            raise ProviderBudgetBlocked("Actual provider cost exceeded its reservation; reservation remains charged")
        self.store.append("outreach_provider_budget", {
            "record_id": f"outreach-budget:{self.job_key}:model:{sequence}:settle",
            "event": "settle_model", "job_key": self.job_key, "sequence": sequence,
            "model": model, "prompt_tokens": prompt, "cached_input_tokens": cached,
            "cache_write_tokens": writes, "cache_write_usage_reported": write_reported,
            "completion_tokens": completion, "actual_cost_usd": float(cost),
            "cost_basis": "provider_usage_with_conservative_cache_write_assumption",
        })
        self.settlements[sequence] = {"actual_cost_usd": float(cost)}

    @staticmethod
    def request_fingerprint(model: str, messages: list[dict], purpose: str, parameters=None) -> str:
        material = json.dumps({"model": model, "messages": messages, "purpose": purpose,
                               "parameters": parameters or {}},
                              ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def replay_model_response(self, model: str, messages: list[dict], purpose: str, count: int = 1, parameters=None):
        """Return an exact prior response for this experiment without provider spend."""
        if self.experiment_id is None:
            return None
        fingerprint = self.request_fingerprint(model, messages, purpose, parameters)
        _, reservations, settlements, _, _ = self._load_ledger()
        records = sorted(
            (row for row in self.store.records("outreach_model_response")
             if row.get("job_key") == self.job_key
             and row.get("experiment_id") == self.experiment_id
             and row.get("request_fingerprint") == fingerprint
             and row.get("purpose") == purpose
             and row.get("model") == model
             and row.get("attempt_id") != self.attempt_id
             and row.get("record_id") not in self.replayed_response_ids
             and int(row.get("reservation_sequence", 0)) in reservations
             and int(row.get("reservation_sequence", 0)) in settlements),
            key=lambda row: int(row.get("reservation_sequence", 0)),
        )
        for row in records:
            outputs = row.get("raw_outputs") or []
            if len(outputs) == count:
                self.replayed_response_ids.add(row["record_id"])
                self.last_response_sequence = int(row["reservation_sequence"])
                self.last_response_record = row
                return outputs
        return None

    def persist_model_response(self, sequence: int, response, model: str, messages: list[dict], purpose: str, parameters=None):
        """Archive provider output before parsing; unresolved archive writes fail closed."""
        _, reservations, _, _, _ = self._load_ledger()
        reservation = reservations.get(int(sequence))
        if reservation is None or int(sequence) in self.settlements:
            raise ProviderBudgetBlocked("Provider response has no unsettled model reservation")
        choices = sorted(getattr(response, "choices", []) or [], key=lambda choice: choice.index)
        outputs = [choice.message.content or "" for choice in choices]
        usage = getattr(response, "usage", None)
        usage_data = None
        if usage is not None:
            details = self._field(usage, "prompt_tokens_details", "input_tokens_details")
            usage_data = {
                "prompt_tokens": int(self._field(usage, "prompt_tokens") or 0),
                "completion_tokens": int(self._field(usage, "completion_tokens") or 0),
                "total_tokens": int(self._field(usage, "total_tokens") or 0),
                "cached_input_tokens": int(self._field(details, "cached_tokens", "cached_input_tokens") or 0),
                "cache_write_tokens": self._field(details, "cache_write_tokens", "cache_creation_tokens"),
            }
        request_id = getattr(response, "id", None)
        response_record = {
            "record_id": f"outreach-response:{self.job_key}:model:{sequence}",
            "job_key": self.job_key,
            "attempt_id": self.attempt_id,
            "experiment_id": self.experiment_id,
            "provider_request_id": request_id,
            "request_fingerprint": self.request_fingerprint(model, messages, purpose, parameters),
            "purpose": purpose,
            "reservation_sequence": int(sequence),
            "model": str(getattr(response, "model", None) or model),
            "usage": usage_data,
            "raw_outputs": outputs,
            "parser_status": "pending",
        }
        self.store.append("outreach_model_response", response_record)
        self.last_response_sequence = int(sequence)
        self.last_response_record = response_record

    def record_response_validation(self, status: str, *, result=None):
        """Append parser/application outcome without duplicating raw provider text."""
        sequence = self.last_response_sequence
        if sequence is None:
            return
        from hashlib import sha256
        raw = getattr(self, "last_response_record", None) or next((item for item in self.store.records("outreach_model_response")
                    if item.get("job_key") == self.job_key
                    and item.get("reservation_sequence") == sequence), None)
        if raw is None:
            raise ProviderBudgetBlocked("The durable provider response archive is missing")
        result_text = None
        result_digest = ""
        if result is not None:
            result_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, sort_keys=True)
            result_digest = sha256(result_text.encode("utf-8")).hexdigest()
        payload = {
            "record_id": f"outreach-response:{self.job_key}:model:{sequence}:validation:{self.attempt_id}:{status}:{result_digest}",
            "job_key": self.job_key,
            "attempt_id": self.attempt_id,
            "source_attempt_id": raw["attempt_id"],
            "provider_request_id": raw.get("provider_request_id"),
            "reservation_sequence": sequence,
            "raw_output_sha256": sha256("\n".join(raw.get("raw_outputs") or []).encode("utf-8")).hexdigest(),
            "parser_status": status,
        }
        if result is not None:
            payload["transformed_result"] = result_text
            payload["transformed_result_sha256"] = result_digest
        self.store.append("outreach_model_response_validation", payload)

def active_outreach_budget():
    return _ACTIVE_OUTREACH_BUDGET.get()


def record_active_provider_response_validation(status: str, *, result=None):
    budget = active_outreach_budget()
    if budget is not None:
        budget.record_response_validation(status, result=result)


class TokenUsageProfiler:
    def __init__(self):
        self.calls = []
        self._token = None

    def __enter__(self):
        self._token = _ACTIVE_PROFILER.set(self)
        return self

    def __exit__(self, *_):
        _ACTIVE_PROFILER.reset(self._token)

    def record(self, *, purpose, requested_model, actual_model, usage, latency_ms):
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        pricing = MODEL_PRICING.get(actual_model) or MODEL_PRICING.get(requested_model)
        if pricing is None and actual_model.startswith("gpt-6-luna-"):
            pricing = MODEL_PRICING["gpt-6-luna"]
        if pricing is None:
            raise ValueError(f"No verified pricing configured for actual model {actual_model!r}")
        if actual_model == "gpt-6-luna" or actual_model.startswith("gpt-6-luna-"):
            accounted_cost, cached, cache_writes, cache_write_reported = OutreachProviderBudget._usage_cost(
                usage, prompt, completion
            )
            cost = float(accounted_cost)
        else:
            cached, cache_writes, cache_write_reported = 0, 0, False
            cost = prompt / 1_000_000 * pricing[0] + completion / 1_000_000 * pricing[1]
        self.calls.append(ProviderCallUsage(
            purpose=purpose,
            requested_model=requested_model,
            actual_model=actual_model,
            prompt_tokens=prompt,
            cached_input_tokens=cached,
            cache_write_tokens=cache_writes,
            cache_write_usage_reported=cache_write_reported,
            completion_tokens=completion,
            total_tokens=prompt + completion,
            latency_ms=latency_ms,
            estimated_cost_usd=cost,
        ))

    def summary(self):
        grouped = {}
        for call in self.calls:
            grouped.setdefault(call.purpose, []).append(call)
        result = []
        for purpose, calls in sorted(grouped.items()):
            result.append({
                "purpose": purpose,
                "models": sorted({call.actual_model for call in calls}),
                "calls": len(calls),
                "average_prompt_tokens": statistics.fmean(call.prompt_tokens for call in calls),
                "average_cached_input_tokens": statistics.fmean(call.cached_input_tokens for call in calls),
                "average_cache_write_tokens": statistics.fmean(call.cache_write_tokens for call in calls),
                "average_completion_tokens": statistics.fmean(call.completion_tokens for call in calls),
                "average_total_tokens": statistics.fmean(call.total_tokens for call in calls),
                "average_latency_ms": statistics.fmean(call.latency_ms for call in calls),
                "average_cost_usd": statistics.fmean(call.estimated_cost_usd for call in calls),
                "actual_cost_usd": sum(call.estimated_cost_usd for call in calls),
            })
        return result

    def export(self, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        rows = [asdict(call) for call in self.calls]
        with (output_dir / "provider_calls.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["purpose"])
            writer.writeheader(); writer.writerows(rows)
        (output_dir / "provider_calls.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def record_provider_usage(**kwargs):
    profiler = _ACTIVE_PROFILER.get()
    if profiler is not None:
        profiler.record(**kwargs)


def measured_stage_projection(stage: str, *, subjective: bool = True, profile_path: Path | None = None):
    """Aggregate the persisted real-pipeline token profile for one stage."""
    path = profile_path or DEFAULT_COST_PROFILE_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"Measured cost profile not found at {path}. "
            "Run profile_geo_replication_cost.py first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        row for row in payload.get("projections", [])
        if row.get("stage") == stage
        and (subjective or row.get("purpose") != "subjective_evaluation")
    ]
    if not rows:
        raise ValueError(f"Measured cost profile contains no projection for {stage!r}.")
    by_purpose = {row["purpose"]: row for row in rows}
    return {
        "profile_path": str(path),
        "profile_queries": payload.get("profile_queries"),
        "rows": rows,
        "answer_calls": by_purpose.get("answer_generation", {}).get("provider_calls", 0),
        "rewrite_calls": by_purpose.get("strategy_rewrite", {}).get("provider_calls", 0),
        "subjective_judge_calls": by_purpose.get("subjective_evaluation", {}).get("provider_calls", 0),
        "total_calls": sum(row["provider_calls"] for row in rows),
        "prompt_tokens": sum(row["prompt_tokens"] for row in rows),
        "completion_tokens": sum(row["completion_tokens"] for row in rows),
        "total_tokens": sum(row["total_tokens"] for row in rows),
        "runtime_seconds": sum(row["estimated_runtime_seconds"] for row in rows),
        "cost_usd": sum(row["estimated_cost_usd"] for row in rows),
    }
