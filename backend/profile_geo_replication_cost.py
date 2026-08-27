import argparse
import csv
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.core.database import SessionLocal
from app.experiment.official_replication_runner import OfficialReplicationRunner
from app.experiment.token_usage_profiler import MODEL_PRICING, TokenUsageProfiler
from app.experiment.trend_validation import STAGES
from app.storage.experiment_repository import ExperimentRepository


PROFILE_QUERIES = 3


def projections(summary):
    rows = []
    for stage, config in STAGES.items():
        factor = config["queries"] / PROFILE_QUERIES
        for category in summary:
            rows.append({
                "stage": stage,
                "queries": config["queries"],
                "purpose": category["purpose"],
                "provider_calls": round(category["calls"] * factor),
                "prompt_tokens": round(category["average_prompt_tokens"] * category["calls"] * factor),
                "completion_tokens": round(category["average_completion_tokens"] * category["calls"] * factor),
                "total_tokens": round(category["average_total_tokens"] * category["calls"] * factor),
                "estimated_runtime_seconds": round(category["average_latency_ms"] * category["calls"] * factor / 1000),
                "estimated_cost_usd": category["actual_cost_usd"] * factor,
            })
    return rows


def write_budget_report(output_dir, profiler, projected):
    summary = profiler.summary()
    stage_costs = {
        stage: sum(row["estimated_cost_usd"] for row in projected if row["stage"] == stage)
        for stage in STAGES
    }
    actual_total = sum(row["actual_cost_usd"] for row in summary)
    lines = [
        "# Princeton GEO Token-Accurate Cost Profile", "",
        f"Profile sample: {PROFILE_QUERIES} official GEO-bench queries using the unchanged full pipeline.", "",
        f"Measured profiling cost: **${actual_total:.4f}**.", "",
        "## Actual model and call graph", "",
        "`OfficialReplicationRunner` → `GeoRewriter` → Chat Completions (strategy rewrite); "
        "`OfficialReplicationRunner` → one Chat Completions request with `n=5` per strategy "
        "(five answers are committed before evaluation); "
        "`ExperimentEvaluationPipeline` → seven legacy Completions calls (Subjective Impression). "
        "PAWC, Word, Position, calibration, statistics, trend verification, export and charting are local and make no provider calls.", "",
        "There is no model fallback. Context-length failures retry the same rewrite model after prompt truncation; every retry is independently metered.", "",
        "**Model identity finding:** the table below reports the actual model identifiers returned by "
        "the API for this profiling run. Costs use those returned identifiers when pricing is configured.", "",
        "## Measured averages", "",
        "| Pipeline stage | Actual calls | Actual model(s) | Avg prompt tokens | Avg completion tokens | Avg total tokens | Avg latency | Avg cost/call |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['purpose']} | {row['calls']} | {', '.join(row['models'])} | "
            f"{row['average_prompt_tokens']:.1f} | {row['average_completion_tokens']:.1f} | "
            f"{row['average_total_tokens']:.1f} | {row['average_latency_ms'] / 1000:.2f}s | "
            f"${row['average_cost_usd']:.6f} |"
        )
    lines += ["", "## Projected budgets", "",
              "| Stage | Purpose | Calls | Prompt tokens | Completion tokens | Total tokens | Runtime | Projected cost | % of stage cost |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in projected:
        percentage = row["estimated_cost_usd"] / stage_costs[row["stage"]] * 100 if stage_costs[row["stage"]] else 0
        lines.append(
            f"| {row['stage']} | {row['purpose']} | {row['provider_calls']:,} | "
            f"{row['prompt_tokens']:,} | {row['completion_tokens']:,} | {row['total_tokens']:,} | "
            f"{row['estimated_runtime_seconds'] / 3600:.2f}h | ${row['estimated_cost_usd']:.2f} | {percentage:.1f}% |"
        )
    totals = {}
    for row in projected:
        total = totals.setdefault(row["stage"], {key: 0 for key in (
            "provider_calls", "prompt_tokens", "completion_tokens", "total_tokens",
            "estimated_runtime_seconds", "estimated_cost_usd",
        )})
        for key in total:
            total[key] += row[key]
    lines += ["", "## Stage totals", "",
              "| Stage | Calls | Prompt tokens | Completion tokens | Total tokens | Sequential runtime | Cost |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for stage in STAGES:
        row = totals[stage]
        lines.append(
            f"| {stage} | {row['provider_calls']:,} | {row['prompt_tokens']:,} | "
            f"{row['completion_tokens']:,} | {row['total_tokens']:,} | "
            f"{row['estimated_runtime_seconds'] / 3600:.2f}h | ${row['estimated_cost_usd']:.2f} |"
        )
    dominant = max(summary, key=lambda row: row["actual_cost_usd"])
    lines += ["", "## Cost concentration", "",
              f"The measured dominant stage is **{dominant['purpose']}**. Affordability is a research-budget decision; this report does not authorize Stage 1.", "",
              f"Stage 1 projects to about **${stage_costs['stage1']:.2f}** and Full to about "
              f"**${stage_costs['full']:.2f}** from this three-query sample. "
              "Without a supplied research-budget ceiling, affordability cannot be answered as a boolean. "
              "The full run is materially expensive and should remain gated; the three-query sample also cannot "
              "eliminate sampling uncertainty from unusually long or short benchmark sources.", "",
              "## Pricing configuration", "",
              f"Configured USD per 1M input/output tokens: `{json.dumps(MODEL_PRICING, sort_keys=True)}`. "
              "Actual response model identifiers, not merely requested aliases, determine the recorded cost.", ""]
    (output_dir / "TokenAccurateCostReport.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Profile exactly three official GEO queries")
    parser.add_argument("--confirm-profile")
    parser.add_argument("--output-dir", default="../verification_artifacts/research_cost_profile")
    args = parser.parse_args()
    if args.confirm_profile != "THREE_QUERIES":
        parser.error("Profiling requires --confirm-profile THREE_QUERIES")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # A fresh rewrite cache measures the cold-path rewrite cost. Reusing the
    # production cache would incorrectly report zero rewrite calls/latency.
    previous_cache = os.environ.get("GEO_CACHE_FILE")
    with tempfile.TemporaryDirectory(prefix="geo-cost-profile-") as temp_dir:
        os.environ["GEO_CACHE_FILE"] = str(Path(temp_dir) / "rewrite_cache.json")
        try:
            with SessionLocal() as db:
                runner = OfficialReplicationRunner(ExperimentRepository(db), subjective=True)
                experiment = runner.create(limit=PROFILE_QUERIES, name="Three-query GEO cost profile")
                profiled_queries = [row["query"] for row in json.loads(experiment.benchmark_queries_json)]
                profiler = TokenUsageProfiler()
                with profiler:
                    runner.execute(experiment.id)
                runner.export(experiment.id, output_dir / f"experiment_{experiment.id}")
                experiment_id = experiment.id
        finally:
            if previous_cache is None:
                os.environ.pop("GEO_CACHE_FILE", None)
            else:
                os.environ["GEO_CACHE_FILE"] = previous_cache
    profiler.export(output_dir)
    summary = profiler.summary()
    projected = projections(summary)
    (output_dir / "cost_profile.json").write_text(json.dumps({
        "profile_queries": PROFILE_QUERIES,
        "profile_query_texts": profiled_queries,
        "experiment_id": experiment_id,
        "profiled_at": datetime.now(timezone.utc).isoformat(),
        "sampling": "deterministic Random(42) subset of valid GEO-bench test rows",
        "rewrite_cache": "cold",
        "measured": summary,
        "projections": projected,
    }, indent=2), encoding="utf-8")
    with (output_dir / "cost_projections.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(projected[0]))
        writer.writeheader(); writer.writerows(projected)
    write_budget_report(output_dir, profiler, projected)
    print(output_dir / "TokenAccurateCostReport.md")


if __name__ == "__main__":
    main()
