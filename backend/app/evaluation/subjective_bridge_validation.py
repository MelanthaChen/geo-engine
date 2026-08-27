"""Standalone bridge validation for Princeton GEO subjective evaluators.

This module deliberately does not participate in the experiment pipeline.  It
contains the API adapters, statistics, plots, and report generation used by
``validate_subjective_evaluator_bridge.py``.
"""

from __future__ import annotations

import csv
import html
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

from app.evaluation.subjective_evaluator import (
    OFFICIAL_PROMPT_FILES,
    SubjectiveImpressionEvaluator,
    calibrate_subjective_scores,
)


LEGACY_MODEL = "gpt-3.5-turbo-instruct"
CANDIDATE_MODEL = "gpt-4o-mini-2024-07-18"
DIMENSIONS = tuple(OFFICIAL_PROMPT_FILES)


@dataclass(frozen=True)
class AnswerSample:
    result_id: int
    run_id: int
    query: str
    answer: str
    selected_rank: int
    strategy: str
    sample_index: int
    pawc: float


@dataclass(frozen=True)
class ScoreObservation:
    result_id: int
    model: str
    actual_model: str
    dimension: str
    score: float
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def expected_score(top_logprobs: dict[str, float]) -> float:
    """Apply Princeton's bounded probability-weighted first-token score."""
    if not top_logprobs:
        raise ValueError("Evaluator returned no first-token log probabilities")
    weights = {token: math.exp(value) for token, value in top_logprobs.items()}
    probability = sum(weights.values())
    if probability == 0:
        raise ValueError("Evaluator returned zero probability mass")
    weighted = 0.0
    for token, weight in weights.items():
        try:
            number = min(5.0, max(1.0, float(token.strip())))
        except (TypeError, ValueError):
            number = 1.0
        weighted += number * weight
    return weighted / probability


class BridgeModelEvaluator:
    """Evaluate one already-generated answer without touching pipeline state."""

    def __init__(self, client, model: str):
        if model not in {LEGACY_MODEL, CANDIDATE_MODEL}:
            raise ValueError(f"Unsupported bridge model: {model}")
        self.client = client
        self.model = model

    def evaluate_dimension(
        self,
        sample: AnswerSample,
        dimension: str,
    ) -> ScoreObservation:
        prompt = SubjectiveImpressionEvaluator._official_prompt(dimension).replace(
            "[1]", f"[{sample.selected_rank}]"
        ).format(query=sample.query, answer=sample.answer)
        started = time.perf_counter()
        if self.model == LEGACY_MODEL:
            response = self.client.completions.create(
                model=self.model,
                prompt=prompt,
                temperature=0,
                max_tokens=3,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                logprobs=5,
                n=1,
            )
            top_logprobs = response.choices[0].logprobs.top_logprobs[0]
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=3,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                logprobs=True,
                top_logprobs=5,
                n=1,
            )
            first = response.choices[0].logprobs.content[0]
            top_logprobs = {
                item.token: item.logprob for item in first.top_logprobs
            }
        usage = response.usage
        return ScoreObservation(
            result_id=sample.result_id,
            model=self.model,
            actual_model=response.model,
            dimension=dimension,
            score=expected_score(top_logprobs),
            prompt_tokens=int(usage.prompt_tokens or 0),
            completion_tokens=int(usage.completion_tokens or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else math.nan


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return math.nan
    x_mean, y_mean = _mean(x), _mean(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    denominator = math.sqrt(
        sum((a - x_mean) ** 2 for a in x)
        * sum((b - y_mean) ** 2 for b in y)
    )
    return numerator / denominator if denominator else math.nan


def average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end][1] == ordered[position][1]:
            end += 1
        rank = ((position + 1) + end) / 2
        for original_index, _ in ordered[position:end]:
            ranks[original_index] = rank
        position = end
    return ranks


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(average_ranks(x), average_ranks(y))


def kendall_tau_b(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return math.nan
    concordant = discordant = ties_x = ties_y = 0
    for left in range(len(x) - 1):
        for right in range(left + 1, len(x)):
            dx = x[left] - x[right]
            dy = y[left] - y[right]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx * dy > 0:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt(
        (concordant + discordant + ties_x)
        * (concordant + discordant + ties_y)
    )
    return (concordant - discordant) / denominator if denominator else math.nan


def agreement_metrics(x: list[float], y: list[float]) -> dict[str, float | int]:
    differences = [b - a for a, b in zip(x, y)]
    bias = _mean(differences)
    sd = statistics.stdev(differences) if len(differences) > 1 else 0.0
    return {
        "n": len(x),
        "pearson": pearson(x, y),
        "spearman": spearman(x, y),
        "kendall_tau_b": kendall_tau_b(x, y),
        "mae": _mean(abs(value) for value in differences),
        "mean_difference_candidate_minus_legacy": bias,
        "bland_altman_lower": bias - 1.96 * sd,
        "bland_altman_upper": bias + 1.96 * sd,
    }


def discretize(value: float) -> int:
    return min(5, max(1, int(math.floor(value + 0.5))))


def confusion_matrix(x: list[float], y: list[float]) -> list[list[int]]:
    matrix = [[0 for _ in range(5)] for _ in range(5)]
    for legacy, candidate in zip(x, y):
        matrix[discretize(legacy) - 1][discretize(candidate) - 1] += 1
    return matrix


def paired_scores(
    samples: list[AnswerSample],
    observations: list[ScoreObservation],
) -> tuple[dict[str, tuple[list[float], list[float]]], dict[int, dict[str, dict[str, float]]]]:
    by_result: dict[int, dict[str, dict[str, float]]] = {
        sample.result_id: {LEGACY_MODEL: {}, CANDIDATE_MODEL: {}}
        for sample in samples
    }
    for observation in observations:
        if observation.result_id in by_result:
            by_result[observation.result_id][observation.model][
                observation.dimension
            ] = observation.score

    pairs: dict[str, tuple[list[float], list[float]]] = {}
    for dimension in DIMENSIONS:
        legacy, candidate = [], []
        for sample in samples:
            values = by_result[sample.result_id]
            if (
                dimension in values[LEGACY_MODEL]
                and dimension in values[CANDIDATE_MODEL]
            ):
                legacy.append(values[LEGACY_MODEL][dimension])
                candidate.append(values[CANDIDATE_MODEL][dimension])
        pairs[dimension] = (legacy, candidate)

    legacy_average, candidate_average = [], []
    for sample in samples:
        values = by_result[sample.result_id]
        if all(d in values[LEGACY_MODEL] for d in DIMENSIONS) and all(
            d in values[CANDIDATE_MODEL] for d in DIMENSIONS
        ):
            legacy_average.append(_mean(values[LEGACY_MODEL].values()))
            candidate_average.append(_mean(values[CANDIDATE_MODEL].values()))
    pairs["subjective_average_raw"] = (legacy_average, candidate_average)
    return pairs, by_result


def calibrated_average_pairs(
    samples: list[AnswerSample],
    by_result: dict[int, dict[str, dict[str, float]]],
) -> tuple[list[float], list[float]]:
    complete = [
        sample
        for sample in samples
        if all(d in by_result[sample.result_id][LEGACY_MODEL] for d in DIMENSIONS)
        and all(d in by_result[sample.result_id][CANDIDATE_MODEL] for d in DIMENSIONS)
    ]
    if not complete:
        return [], []
    pawc = [sample.pawc for sample in complete]
    model_averages: dict[str, list[list[float]]] = {
        LEGACY_MODEL: [],
        CANDIDATE_MODEL: [],
    }
    for model in model_averages:
        for dimension in DIMENSIONS:
            raw = [by_result[s.result_id][model][dimension] for s in complete]
            model_averages[model].append(calibrate_subjective_scores(raw, pawc))
    return tuple(
        [
            _mean(dimension_values[index] for dimension_values in model_averages[model])
            for index in range(len(complete))
        ]
        for model in (LEGACY_MODEL, CANDIDATE_MODEL)
    )


def _scale(value: float, low: float, high: float, start: float, end: float) -> float:
    return (start + end) / 2 if high == low else start + (value - low) * (end - start) / (high - low)


def write_scatter_svg(path: Path, x: list[float], y: list[float], title: str) -> None:
    width, height, margin = 760, 600, 70
    low = min(x + y + [1.0])
    high = max(x + y + [5.0])
    points = []
    for left, right in zip(x, y):
        px = _scale(left, low, high, margin, width - margin)
        py = _scale(right, low, high, height - margin, margin)
        points.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="5" fill="#2563eb" fill-opacity="0.65"/>')
    diagonal_start = _scale(low, low, high, margin, width - margin)
    diagonal_end = _scale(high, low, high, margin, width - margin)
    path.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="white"/>
<text x="{width/2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="18">{html.escape(title)}</text>
<line x1="{diagonal_start}" y1="{height-margin}" x2="{diagonal_end}" y2="{margin}" stroke="#9ca3af" stroke-dasharray="6 5"/>
<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>
<line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" stroke="black"/>
{''.join(points)}
<text x="{width/2}" y="{height-18}" text-anchor="middle" font-family="sans-serif">Legacy score</text>
<text transform="translate(18 {height/2}) rotate(-90)" text-anchor="middle" font-family="sans-serif">Candidate score</text>
</svg>''',
        encoding="utf-8",
    )


def write_bland_altman_svg(path: Path, x: list[float], y: list[float]) -> None:
    means = [(a + b) / 2 for a, b in zip(x, y)]
    differences = [b - a for a, b in zip(x, y)]
    stats = agreement_metrics(x, y)
    width, height, margin = 760, 600, 70
    x_low, x_high = min(means + [1.0]), max(means + [5.0])
    limits = [
        float(stats["bland_altman_lower"]),
        float(stats["mean_difference_candidate_minus_legacy"]),
        float(stats["bland_altman_upper"]),
    ]
    y_low, y_high = min(differences + limits), max(differences + limits)
    if y_low == y_high:
        y_low, y_high = y_low - 1, y_high + 1
    points = []
    for mean, difference in zip(means, differences):
        px = _scale(mean, x_low, x_high, margin, width - margin)
        py = _scale(difference, y_low, y_high, height - margin, margin)
        points.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="#7c3aed" fill-opacity="0.65"/>')
    lines = []
    for value, color in zip(limits, ("#dc2626", "#111827", "#dc2626")):
        py = _scale(value, y_low, y_high, height - margin, margin)
        lines.append(f'<line x1="{margin}" y1="{py:.2f}" x2="{width-margin}" y2="{py:.2f}" stroke="{color}" stroke-dasharray="6 5"/>')
    path.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="white"/>
<text x="{width/2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="18">Bland–Altman: all facet scores</text>
<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>
<line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" stroke="black"/>
{''.join(lines)}{''.join(points)}
<text x="{width/2}" y="{height-18}" text-anchor="middle" font-family="sans-serif">Mean of evaluator scores</text>
<text transform="translate(18 {height/2}) rotate(-90)" text-anchor="middle" font-family="sans-serif">Candidate − legacy</text>
</svg>''',
        encoding="utf-8",
    )


def write_confusion_svg(path: Path, matrix: list[list[int]], title: str) -> None:
    cell, margin, top = 72, 78, 64
    width, height = margin * 2 + cell * 5, top + margin + cell * 5
    maximum = max((value for row in matrix for value in row), default=1) or 1
    cells = []
    for row in range(5):
        for column in range(5):
            value = matrix[row][column]
            intensity = int(245 - 175 * value / maximum)
            fill = f"rgb({intensity},{intensity + 5},{255})"
            x, y = margin + column * cell, top + row * cell
            cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}" stroke="white"/><text x="{x+cell/2}" y="{y+cell/2+5}" text-anchor="middle" font-family="sans-serif">{value}</text>')
    labels = []
    for index in range(5):
        labels.append(f'<text x="{margin+index*cell+cell/2}" y="{top+cell*5+25}" text-anchor="middle" font-family="sans-serif">{index+1}</text>')
        labels.append(f'<text x="{margin-20}" y="{top+index*cell+cell/2+5}" text-anchor="middle" font-family="sans-serif">{index+1}</text>')
    path.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="white"/>
<text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">{html.escape(title)}</text>
{''.join(cells)}{''.join(labels)}
<text x="{width/2}" y="{height-10}" text-anchor="middle" font-family="sans-serif">Candidate class</text>
<text transform="translate(18 {top+cell*2.5}) rotate(-90)" text-anchor="middle" font-family="sans-serif">Legacy class</text></svg>''',
        encoding="utf-8",
    )


def strategy_direction_agreement(
    samples: list[AnswerSample],
    by_result: dict[int, dict[str, dict[str, float]]],
) -> dict[str, object]:
    values: dict[str, dict[str, list[float]]] = {}
    for sample in samples:
        scores = by_result[sample.result_id]
        if all(d in scores[LEGACY_MODEL] for d in DIMENSIONS) and all(
            d in scores[CANDIDATE_MODEL] for d in DIMENSIONS
        ):
            bucket = values.setdefault(
                sample.strategy, {LEGACY_MODEL: [], CANDIDATE_MODEL: []}
            )
            for model in (LEGACY_MODEL, CANDIDATE_MODEL):
                bucket[model].append(_mean(scores[model].values()))
    if "original" not in values:
        return {"comparable_strategies": 0, "agreement": math.nan, "details": []}
    baseline = {
        model: _mean(values["original"][model])
        for model in (LEGACY_MODEL, CANDIDATE_MODEL)
    }
    details = []
    for strategy, model_values in sorted(values.items()):
        if strategy == "original":
            continue
        legacy_delta = _mean(model_values[LEGACY_MODEL]) - baseline[LEGACY_MODEL]
        candidate_delta = _mean(model_values[CANDIDATE_MODEL]) - baseline[CANDIDATE_MODEL]
        details.append(
            {
                "strategy": strategy,
                "legacy_delta": legacy_delta,
                "candidate_delta": candidate_delta,
                "same_direction": (legacy_delta >= 0) == (candidate_delta >= 0),
                "n": len(model_values[LEGACY_MODEL]),
            }
        )
    return {
        "comparable_strategies": len(details),
        "agreement": _mean(float(row["same_direction"]) for row in details),
        "details": details,
    }


def generate_outputs(
    output_dir: Path,
    samples: list[AnswerSample],
    observations: list[ScoreObservation],
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pairs, by_result = paired_scores(samples, observations)
    calibrated = calibrated_average_pairs(samples, by_result)
    pairs["subjective_average_calibrated"] = calibrated
    metrics = {
        name: agreement_metrics(legacy, candidate)
        for name, (legacy, candidate) in pairs.items()
    }
    directions = strategy_direction_agreement(samples, by_result)
    provider_summary = {}
    for model in (LEGACY_MODEL, CANDIDATE_MODEL):
        rows = [row for row in observations if row.model == model]
        provider_summary[model] = {
            "actual_models": sorted({row.actual_model for row in rows}),
            "calls": len(rows),
            "prompt_tokens": sum(row.prompt_tokens for row in rows),
            "completion_tokens": sum(row.completion_tokens for row in rows),
            "average_latency_ms": _mean(row.latency_ms for row in rows),
        }

    with (output_dir / "paired_scores.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["result_id", "strategy", "dimension", "legacy", "candidate"])
        for sample in samples:
            scores = by_result[sample.result_id]
            for dimension in DIMENSIONS:
                if dimension in scores[LEGACY_MODEL] and dimension in scores[CANDIDATE_MODEL]:
                    writer.writerow([sample.result_id, sample.strategy, dimension, scores[LEGACY_MODEL][dimension], scores[CANDIDATE_MODEL][dimension]])

    with (output_dir / "agreement_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["dimension", *next(iter(metrics.values())).keys()]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for name, row in metrics.items():
            writer.writerow({"dimension": name, **row})

    all_legacy, all_candidate = [], []
    for dimension in DIMENSIONS:
        legacy, candidate = pairs[dimension]
        all_legacy.extend(legacy)
        all_candidate.extend(candidate)
        write_scatter_svg(output_dir / f"scatter_{dimension}.svg", legacy, candidate, f"{dimension}: evaluator agreement")
        matrix = confusion_matrix(legacy, candidate)
        write_confusion_svg(output_dir / f"confusion_{dimension}.svg", matrix, f"{dimension}: rounded 1–5 scores")
        with (output_dir / f"confusion_{dimension}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["legacy\\candidate", 1, 2, 3, 4, 5])
            for index, row in enumerate(matrix, start=1):
                writer.writerow([index, *row])
    write_scatter_svg(output_dir / "scatter_subjective_average.svg", *pairs["subjective_average_raw"], "Raw subjective average")
    write_bland_altman_svg(output_dir / "bland_altman_all_dimensions.svg", all_legacy, all_candidate)

    primary = metrics["subjective_average_raw"]
    dimension_passes = sum(
        1 for dimension in DIMENSIONS
        if float(metrics[dimension]["spearman"]) >= 0.70
    )
    direction_value = float(directions["agreement"])
    has_strategy_evidence = int(directions["comparable_strategies"]) >= 3
    passed = (
        int(primary["n"]) == len(samples)
        and float(primary["spearman"]) >= 0.80
        and float(primary["kendall_tau_b"]) >= 0.65
        and float(primary["mae"]) <= 0.50
        and dimension_passes >= 6
        and has_strategy_evidence
        and direction_value >= 0.80
    )
    decision = "SUPPORTED" if passed else "NOT_SUPPORTED"
    limitations = []
    if len(samples) == 20:
        limitations.append("Twenty answers provide a bridge screen, not definitive measurement invariance evidence.")
    if not has_strategy_evidence:
        limitations.append("The random sample did not contain baseline plus at least three comparable strategies; paper-conclusion preservation is not estimable from this sample.")
    limitations.append("The candidate uses chat-message framing because GPT-4o mini does not support legacy Completions.")

    report = [
        "# Subjective Evaluator Bridge Validation",
        "",
        f"**Decision: {decision}**",
        "",
        f"Sample: {len(samples)} completed experiment answers; {len(observations)} dimension-level model observations.",
        "",
        "## Predeclared decision rule",
        "",
        "Replacement is supported only when the raw seven-facet average has Spearman ≥ 0.80, Kendall τ-b ≥ 0.65, MAE ≤ 0.50, at least six of seven facets have Spearman ≥ 0.70, and at least 80% of three or more strategy-vs-baseline effects retain direction.",
        "",
        "## Agreement",
        "",
        "| Dimension | N | Pearson | Spearman | Kendall τ-b | MAE | Bias |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in metrics.items():
        report.append(
            f"| {name} | {row['n']} | {float(row['pearson']):.4f} | {float(row['spearman']):.4f} | {float(row['kendall_tau_b']):.4f} | {float(row['mae']):.4f} | {float(row['mean_difference_candidate_minus_legacy']):.4f} |"
        )
    report.extend([
        "",
        "## Provider observations",
        "",
        "| Requested model | Actual model identifiers | Calls | Prompt tokens | Completion tokens | Average latency |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for model, row in provider_summary.items():
        report.append(
            f"| {model} | {', '.join(row['actual_models'])} | {row['calls']} | {row['prompt_tokens']} | {row['completion_tokens']} | {float(row['average_latency_ms']):.0f} ms |"
        )
    report.extend([
        "",
        "## Paper-conclusion direction check",
        "",
        f"Comparable strategies: {directions['comparable_strategies']}; direction agreement: {direction_value:.1%}.",
        "",
        "| Strategy | N | Legacy Δ vs baseline | Candidate Δ vs baseline | Same direction |",
        "|---|---:|---:|---:|:---:|",
    ])
    for row in directions["details"]:
        report.append(f"| {row['strategy']} | {row['n']} | {row['legacy_delta']:.4f} | {row['candidate_delta']:.4f} | {'Yes' if row['same_direction'] else 'No'} |")
    report.extend([
        "",
        "## Scientific interpretation",
        "",
        (
            "The observed bridge meets the predeclared screening rule. Replacing the evaluator is scientifically defensible as a disclosed contemporary evaluator migration; it is still not an exact historical reproduction."
            if passed else
            "The observed bridge does not meet the predeclared screening rule. The candidate evaluator should not replace the legacy evaluator for claims that depend on Princeton's subjective conclusions without a larger or revised validation."
        ),
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in limitations],
        "",
        "## Artifacts",
        "",
        "- `agreement_metrics.csv`",
        "- `paired_scores.csv`",
        "- `bland_altman_all_dimensions.svg`",
        "- `scatter_*.svg`",
        "- `confusion_*.csv` and `confusion_*.svg`",
    ])
    (output_dir / "BridgeValidationReport.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    summary = {"decision": decision, "metrics": metrics, "strategy_direction": directions, "provider_summary": provider_summary, "limitations": limitations}
    (output_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8")
    return summary


def save_checkpoint(path: Path, samples: list[AnswerSample], observations: list[ScoreObservation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"samples": [asdict(item) for item in samples], "observations": [asdict(item) for item in observations]}, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_checkpoint(path: Path) -> tuple[list[AnswerSample], list[ScoreObservation]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ([AnswerSample(**item) for item in payload["samples"]], [ScoreObservation(**item) for item in payload["observations"]])


def evaluate_with_retries(
    operation: Callable[[], ScoreObservation],
    *,
    attempts: int = 6,
    sleep: Callable[[float], None] = time.sleep,
) -> ScoreObservation:
    for attempt in range(attempts):
        try:
            return operation()
        except Exception:
            if attempt == attempts - 1:
                raise
            sleep(min(60.0, 2.0 ** attempt))
    raise RuntimeError("unreachable")
