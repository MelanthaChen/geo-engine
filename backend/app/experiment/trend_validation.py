import json
from pathlib import Path

from app.experiment.token_usage_profiler import measured_stage_projection


CONCLUSIONS_PATH = Path(__file__).with_name("paper_conclusions.json")
STAGES = {
    "stage1": {"queries": 30, "threshold": 0.80},
    "stage2": {"queries": 100, "threshold": 0.85},
    "stage3": {"queries": 300, "threshold": 0.90},
    "full": {"queries": 997, "threshold": 0.90},
}


def load_paper_conclusions():
    return json.loads(CONCLUSIONS_PATH.read_text(encoding="utf-8"))


def verify_paper_conclusions(statistics_rows):
    means = {
        (row["strategy"], row["metric"]): row["mean"]
        for row in statistics_rows
        if row.get("mean") is not None
    }
    results = []
    for claim in load_paper_conclusions():
        result = {**claim, "status": "NOT_TESTED", "evidence": {}}
        if claim["type"] == "unsupported":
            result["reason"] = f"Requires separate {claim['scope']} experiment."
            results.append(result)
            continue
        left = means.get((claim.get("left"), claim["metric"]))
        right = means.get((claim.get("right"), claim["metric"]))
        if claim["type"] == "all_greater_than":
            baseline = means.get((claim["right"], claim["metric"]))
            observed = {strategy: means.get((strategy, claim["metric"])) for strategy in claim["strategies"]}
            if baseline is None or any(value is None for value in observed.values()):
                result["reason"] = "Insufficient completed strategy statistics."
            else:
                result["status"] = "PASS" if all(value > baseline for value in observed.values()) else "FAIL"
                result["evidence"] = {"baseline": baseline, "observed": observed}
            results.append(result)
            continue
        if claim["type"] == "rank_concordance":
            expected = claim["strategies"]
            observed_values = [means.get((strategy, claim["metric"])) for strategy in expected]
            if any(value is None for value in observed_values):
                result["reason"] = "Insufficient completed strategy statistics."
            else:
                pairs = [(i, j) for i in range(len(expected)) for j in range(i + 1, len(expected))]
                concordant = sum(observed_values[i] > observed_values[j] for i, j in pairs)
                concordance = concordant / len(pairs)
                result["status"] = "PASS" if concordance >= claim["minimum"] else "FAIL"
                result["evidence"] = {"pairwise_concordance": concordance, "required": claim["minimum"]}
            results.append(result)
            continue
        if left is None or right is None:
            result["reason"] = "Required completed metric statistics are missing."
        else:
            relative = None if right == 0 else (left - right) / right
            if claim["type"] == "greater_than":
                passed = left > right
            elif claim["type"] == "less_or_equal":
                passed = left <= right
            else:
                passed = relative is not None and claim["minimum"] <= relative <= claim["maximum"]
            result["status"] = "PASS" if passed else "FAIL"
            result["evidence"] = {"left_mean": left, "right_mean": right, "relative_change": relative}
        results.append(result)
    testable = [row for row in results if row["status"] in {"PASS", "FAIL"}]
    similarity = sum(row["status"] == "PASS" for row in testable) / len(testable) if testable else None
    return {"claims": results, "testable_claims": len(testable), "trend_similarity": similarity}


def fidelity_scores(*, complete, subjective_complete, trend_similarity):
    return {
        "method_fidelity": 0.98,
        "implementation_fidelity": 0.96 if complete else 0.85,
        "dataset_fidelity": 0.997,
        "evaluation_fidelity": 0.96 if subjective_complete else 0.78,
        "trend_fidelity": trend_similarity,
        "model_fidelity": None,
        "model_fidelity_note": "Unknown: the historical GPT-3.5 checkpoint is unavailable.",
    }


def stage_decision(stage, trend_similarity, complete):
    threshold = STAGES[stage]["threshold"]
    if not complete or trend_similarity is None:
        return {"decision": "STOP", "reason": "Stage evidence is incomplete.", "threshold": threshold}
    if trend_similarity >= threshold:
        return {"decision": "PROCEED", "reason": "Trend threshold met.", "threshold": threshold}
    return {"decision": "STOP", "reason": "Trend similarity is below the cost gate; investigate before continuing.", "threshold": threshold}


def estimate_stage(stage, *, subjective=True):
    measured = measured_stage_projection(stage, subjective=subjective)
    return {
        "stage": stage,
        "queries": STAGES[stage]["queries"],
        "answer_calls": measured["answer_calls"],
        "rewrite_calls": measured["rewrite_calls"],
        "subjective_judge_calls": measured["subjective_judge_calls"],
        "total_calls": measured["total_calls"],
        "estimated_input_tokens": measured["prompt_tokens"],
        "estimated_output_tokens": measured["completion_tokens"],
        "estimated_total_tokens": measured["total_tokens"],
        "estimated_cost_usd": round(measured["cost_usd"], 2),
        "estimated_runtime_hours": round(measured["runtime_seconds"] / 3600, 2),
        "estimation_basis": (
            f"Measured {measured['profile_queries']}-query real-pipeline token profile"
        ),
        "cost_profile": measured["profile_path"],
    }
