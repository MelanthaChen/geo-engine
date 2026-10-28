import csv
import json
import statistics
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from pathlib import Path


# USD per 1M tokens, verified against official model pages on 2026-08-20.
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

    MAX_COST_USD = 0.25
    MAX_MODEL_CALLS = 5
    MAX_INPUT_BYTES_PER_CALL = 48000
    MAX_INPUT_TOKENS_PER_CALL = MAX_INPUT_BYTES_PER_CALL
    MAX_OUTPUT_TOKENS_PER_CALL = 1024
    SEARCH_COST_USD = {"exa": 0.007, "brave": 0.005}

    def __init__(self, durable_store, job_key: str):
        self.store = durable_store
        self.job_key = job_key
        self._token = None
        self.reservations = []
        self.settlements = {}
        self.search_reserved = False
        self.search_settled = False
        for record in self.store.records("outreach_provider_budget"):
            if record.get("job_key") != job_key:
                continue
            if record.get("event") == "reserve_model":
                self.reservations.append(record)
            elif record.get("event") == "settle_model":
                self.settlements[int(record["sequence"])] = record
            elif record.get("event") == "reserve_search":
                self.search_reserved = True
            elif record.get("event") == "settle_search":
                self.search_settled = True

    def __enter__(self):
        self._token = _ACTIVE_OUTREACH_BUDGET.set(self)
        return self

    def __exit__(self, *_):
        _ACTIVE_OUTREACH_BUDGET.reset(self._token)

    @property
    def committed_and_reserved_cost(self):
        records = [r for r in self.store.records("outreach_provider_budget") if r.get("job_key") == self.job_key]
        search_reserve = next((r for r in records if r.get("event") == "reserve_search"), None)
        search_settlement = next((r for r in records if r.get("event") == "settle_search"), None)
        search = float(
            search_settlement.get("actual_cost_usd") if search_settlement
            else (search_reserve or {}).get("worst_case_cost_usd", 0)
        )
        model = 0.0
        for reservation in self.reservations:
            sequence = int(reservation["sequence"])
            settled = self.settlements.get(sequence)
            model += float(settled.get("actual_cost_usd") if settled else reservation["worst_case_cost_usd"])
        return search + model

    def reserve_search(self, provider_name: str):
        provider = provider_name.lower()
        if provider not in self.SEARCH_COST_USD:
            raise ProviderBudgetBlocked("The one-job budget has no verified price for this search provider")
        if self.search_reserved:
            raise ProviderBudgetBlocked("This durable job has already reserved its only search request")
        cost = self.SEARCH_COST_USD[provider]
        self._check_budget(cost)
        self.store.append("outreach_provider_budget", {
            "record_id": f"outreach-budget:{self.job_key}:search", "event": "reserve_search",
            "job_key": self.job_key, "provider": provider, "worst_case_cost_usd": cost,
        })
        self.search_reserved = True

    def settle_search(self, provider_name: str, returned_documents: int):
        provider = provider_name.lower()
        if not self.search_reserved or self.search_settled or provider not in self.SEARCH_COST_USD:
            raise ProviderBudgetBlocked("Search usage cannot be settled against this job's reservation")
        self.store.append("outreach_provider_budget", {
            "record_id": f"outreach-budget:{self.job_key}:search:settle",
            "event": "settle_search", "job_key": self.job_key,
            "provider": provider, "returned_documents": int(returned_documents),
            "actual_cost_usd": self.SEARCH_COST_USD[provider],
        })
        self.search_settled = True

    def reserve_model(self, model: str, messages: list[dict], max_output_tokens: int) -> int:
        if model != "gpt-6-luna":
            raise ProviderBudgetBlocked("Outreach research is restricted to the bounded GPT-6 Luna model path")
        if len(self.reservations) >= self.MAX_MODEL_CALLS:
            raise ProviderBudgetBlocked("The durable job has exhausted its five model-call allowance")
        if max_output_tokens < 1 or max_output_tokens > self.MAX_OUTPUT_TOKENS_PER_CALL:
            raise ProviderBudgetBlocked("Model output token cap exceeds the one-job budget")
        input_bytes = sum(len(str(message.get("content") or "").encode("utf-8")) for message in messages)
        if input_bytes > self.MAX_INPUT_BYTES_PER_CALL:
            raise ProviderBudgetBlocked("Model input exceeds the one-job token cap")
        input_rate, output_rate = MODEL_PRICING[model]
        worst = self.MAX_INPUT_TOKENS_PER_CALL / 1_000_000 * input_rate + max_output_tokens / 1_000_000 * output_rate
        self._check_budget(worst)
        sequence = max([int(r["sequence"]) for r in self.reservations] or [0]) + 1
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
        pricing = MODEL_PRICING.get(model) or (MODEL_PRICING["gpt-6-luna"] if model.startswith("gpt-6-luna-") else None)
        if usage is None or pricing is None:
            raise ProviderBudgetBlocked("Provider usage or pricing is unavailable; reservation remains charged")
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        reservation = next(r for r in self.reservations if int(r["sequence"]) == sequence)
        if prompt > int(reservation["input_token_limit"]) or completion > int(reservation["output_token_limit"]):
            raise ProviderBudgetBlocked("Actual provider usage exceeded its reserved token bound")
        input_rate, output_rate = pricing
        cost = prompt / 1_000_000 * input_rate + completion / 1_000_000 * output_rate
        self.store.append("outreach_provider_budget", {
            "record_id": f"outreach-budget:{self.job_key}:model:{sequence}:settle",
            "event": "settle_model", "job_key": self.job_key, "sequence": sequence,
            "model": model, "prompt_tokens": prompt, "completion_tokens": completion,
            "actual_cost_usd": cost,
        })
        self.settlements[sequence] = {"actual_cost_usd": cost}

    def _check_budget(self, next_cost: float):
        if self.committed_and_reserved_cost + next_cost > self.MAX_COST_USD:
            raise ProviderBudgetBlocked("The remaining worst-case provider spend would exceed the $0.25 job cap")


def active_outreach_budget():
    return _ACTIVE_OUTREACH_BUDGET.get()


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
        cost = prompt / 1_000_000 * pricing[0] + completion / 1_000_000 * pricing[1]
        self.calls.append(ProviderCallUsage(
            purpose=purpose,
            requested_model=requested_model,
            actual_model=actual_model,
            prompt_tokens=prompt,
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
