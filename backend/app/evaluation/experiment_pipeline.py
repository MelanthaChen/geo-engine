import math
import statistics
from dataclasses import asdict

from app.evaluation.evaluator import Evaluator
from app.evaluation.subjective_evaluator import SubjectiveImpressionEvaluator


METRIC_UNITS = {
    "word_count": "words",
    "position": "sentence_index",
    "pawc": "ratio",
    "word_score": "ratio",
    "position_score": "ratio",
    "citation_count": "citations",
    "visibility_score": "ratio",
    "response_length": "characters",
    "latency": "milliseconds",
}


class ExperimentEvaluationPipeline:
    """Evaluates completed generations without coupling evaluation to the LLM call."""

    name = "princeton_geo_citation"
    version = "1.0"

    def __init__(
        self,
        evaluator: Evaluator | None = None,
        subjective_evaluator: SubjectiveImpressionEvaluator | None = None,
    ):
        self.evaluator = evaluator or Evaluator()
        self.subjective_evaluator = subjective_evaluator

    def evaluate_outputs(self, outputs, *, selected_document):
        for output in outputs:
            result = self.evaluator.evaluate(
                answer=output["answer"],
                selected_document_text=output["modified_document_text"],
                selected_title=selected_document.title,
                selected_url=selected_document.url,
                selected_rank=selected_document.rank,
            )
            output["evaluation"] = result
            output["evaluation_record"] = {
                "evaluator": self.name,
                "evaluator_version": self.version,
                "details": asdict(result),
                "metrics": {
                    **{key: value for key, value in asdict(result).items()},
                    "response_length": len(output["answer"] or ""),
                    "latency": output.get("latency_ms"),
                },
            }
            if self.subjective_evaluator is not None:
                subjective = self.subjective_evaluator.evaluate(
                    query=output["query"],
                    answer=output["answer"],
                    selected_rank=selected_document.rank,
                )
                output["evaluation_record"]["metrics"].update(
                    {f"subjective_{name}": value for name, value in subjective.scores.items()}
                    | {"subjective_impression_raw": subjective.average}
                )
        return outputs


def descriptive_statistics(values: list[float]) -> dict:
    cleaned = [float(value) for value in values if value is not None]
    count = len(cleaned)
    if not cleaned:
        return {key: None for key in (
            "mean", "median", "variance", "stddev", "min", "max",
            "confidence_low", "confidence_high",
        )} | {"sample_count": 0, "confidence_level": 0.95}

    mean = statistics.fmean(cleaned)
    variance = statistics.variance(cleaned) if count > 1 else 0.0
    stddev = math.sqrt(variance)
    margin = 1.96 * stddev / math.sqrt(count) if count > 1 else 0.0
    return {
        "sample_count": count,
        "mean": mean,
        "median": statistics.median(cleaned),
        "variance": variance,
        "stddev": stddev,
        "min": min(cleaned),
        "max": max(cleaned),
        "confidence_level": 0.95,
        "confidence_low": mean - margin,
        "confidence_high": mean + margin,
    }
