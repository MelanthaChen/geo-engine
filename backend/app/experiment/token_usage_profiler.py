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
