import csv
import json
import random
import time
from pathlib import Path

from app.evaluation.experiment_pipeline import ExperimentEvaluationPipeline
from app.evaluation.subjective_evaluator import (
    SubjectiveImpressionEvaluator,
    calibrate_subjective_scores,
)
from app.experiment.geo_bench_loader import GeoBenchLoader
from app.experiment.replication_figure import write_pawc_bar_chart
from app.experiment.trend_validation import (
    STAGES,
    fidelity_scores,
    stage_decision,
    verify_paper_conclusions,
)
from app.ge.geo_rewriter import GeoRewriter, STRATEGY_LABELS
from app.ge.llm_runner import OpenAILLMRunner
from app.ge.prompt_builder import PromptBuilder
from app.ge.search_provider import RetrievedDocument
from app.storage.experiment_repository import ExperimentRepository


OFFICIAL_ANSWER_MODEL = "gpt-3.5-turbo-16k"
OFFICIAL_ANSWER_TEMPERATURE = 0.5
OFFICIAL_ANSWER_TOP_P = 1
OFFICIAL_ANSWER_MAX_TOKENS = 1024
OFFICIAL_ANSWER_COUNT = 5


class OfficialReplicationRunner:
    """Crash-safe runner for the public GEO-bench test experiment."""

    def __init__(self, repository: ExperimentRepository, *, subjective=False):
        self.repository = repository
        self.llm = OpenAILLMRunner("chatgpt")
        self.rewriter = GeoRewriter(self.llm)
        self.prompt_builder = PromptBuilder()
        self.pipeline = ExperimentEvaluationPipeline(
            subjective_evaluator=(SubjectiveImpressionEvaluator() if subjective else None)
        )
        self.loader = GeoBenchLoader()

    def create(self, *, limit=None, stage=None, name="Official Princeton GEO Replication"):
        entries = self.loader.load_test_entries(1000)
        query_count = STAGES[stage]["queries"] if stage else (limit or len(entries))
        if query_count < len(entries):
            random.Random(42).shuffle(entries)
            entries = entries[:query_count]
        stage_label = stage or f"custom-{len(entries)}"
        return self.repository.create_run(
            property_id=None,
            name=name,
            description=f"Official GEO-bench staged replication: {stage_label}",
            llm_model=OFFICIAL_ANSWER_MODEL,
            provider="chatgpt",
            dataset_name="geo_bench",
            benchmark_queries=entries,
            strategies=list(STRATEGY_LABELS),
            metrics=["pawc", "word_score", "position_score", "subjective_impression"],
            number_of_queries=len(entries),
            random_seed=42,
            temperature=OFFICIAL_ANSWER_TEMPERATURE,
        )

    def execute(self, experiment_id: int):
        experiment = self.repository.get_run(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        if (
            experiment.llm_model != OFFICIAL_ANSWER_MODEL
            or experiment.temperature != OFFICIAL_ANSWER_TEMPERATURE
        ):
            raise ValueError(
                "This run was configured with pre-fidelity answer-generation settings. "
                "Create a new official replication run before execution."
            )
        entries = json.loads(experiment.benchmark_queries_json or "[]")
        self.repository.mark_running(experiment)
        for query_index, entry in enumerate(entries):
            documents = self._documents(entry)
            target = next(d for d in documents if d.is_optimization_target)
            query_row = self.repository.ensure_experiment_query(
                experiment,
                query=entry["query"],
                seed_value=query_index,
                documents=documents,
                selected_document_rank=target.rank,
            )
            for strategy in json.loads(experiment.strategies_json or "[]"):
                sample_group = self.repository.strategy_sample_group(
                    experiment_id=experiment.id,
                    experiment_query_id=query_row.id,
                    strategy=strategy,
                )
                completed = [run for run in sample_group if run.status == "completed"]
                generated = [run for run in sample_group if run.status == "generated"]
                if len(completed) == OFFICIAL_ANSWER_COUNT:
                    continue
                if sample_group:
                    indexes = sorted(run.sample_index for run in sample_group)
                    if indexes != list(range(OFFICIAL_ANSWER_COUNT)) or not generated:
                        raise RuntimeError(
                            "Cannot faithfully resume a legacy partial strategy group; "
                            "official n=5 choices must be generated and stored as one batch."
                        )
                else:
                    modified = self.rewriter.rewrite(
                        document_text=target.plain_text,
                        query=entry["query"],
                        strategy=strategy,
                        model=experiment.llm_model,
                        temperature=experiment.temperature,
                    )
                    prompt = self.prompt_builder.build(
                        query=entry["query"], documents=documents,
                        selected_rank=target.rank, modified_document_text=modified,
                    )
                    started = time.perf_counter()
                    answers = self.llm.generate_many(
                        system_prompt="", user_prompt=prompt,
                        model=OFFICIAL_ANSWER_MODEL,
                        temperature=OFFICIAL_ANSWER_TEMPERATURE,
                        count=OFFICIAL_ANSWER_COUNT,
                        top_p=OFFICIAL_ANSWER_TOP_P,
                        max_tokens=OFFICIAL_ANSWER_MAX_TOKENS,
                        purpose="answer_generation",
                    )
                    generated = self.repository.store_generated_batch(
                        experiment,
                        query_row,
                        query=entry["query"],
                        strategy=strategy,
                        modified_document_text=modified,
                        prompt=prompt,
                        answers=answers,
                        seed_value=query_index,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                    )

                for run in generated:
                    result = run.strategy_result
                    output = {
                        "query": entry["query"], "strategy": strategy,
                        "sample_index": run.sample_index,
                        "modified_document_text": result.modified_document_text,
                        "prompt": result.prompt,
                        "answer": result.answer,
                        "latency_ms": run.latency_ms,
                    }
                    self.pipeline.evaluate_outputs([output], selected_document=target)
                    self.repository.complete_generated_sample(run, output=output)
            self.repository.update_progress(
                experiment,
                current_query=entry["query"],
                current_strategy="completed",
                completed_queries=query_index + 1,
            )
        self._calibrate_subjective(experiment)
        self.repository.mark_completed(experiment)
        return experiment

    def export(self, experiment_id: int, output_dir: Path):
        experiment = self.repository.get_run(experiment_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        rows = self.repository.experiment_csv_rows(experiment)
        with (output_dir / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
            fields = sorted(set().union(*(row.keys() for row in rows))) if rows else ["experiment_id"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        payload = self.repository.serialize(experiment)
        (output_dir / "replication.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        summary = [
            {"strategy": row["strategy"], "pawc_mean": row["mean"] * 100,
             "pawc_stddev": row["stddev"] * 100, "sample_count": row["sampleCount"]}
            for row in payload["statistics"] if row["metric"] == "pawc"
        ]
        with (output_dir / "paper_objective_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["strategy", "pawc_mean", "pawc_stddev", "sample_count"])
            writer.writeheader(); writer.writerows(summary)
        write_pawc_bar_chart(summary, output_dir / "paper_objective_metrics.png")
        paper_rows = [
            {
                "strategy": row["strategy"],
                "metric": row["metric"],
                "mean": row["mean"] * 100,
                "stddev": row["stddev"] * 100,
                "sample_count": row["sampleCount"],
            }
            for row in payload["statistics"]
            if row["metric"] in {
                "pawc", "word_score", "position_score",
                "subjective_impression_calibrated",
                "subjective_relevance_calibrated", "subjective_influence_calibrated",
                "subjective_uniqueness_calibrated", "subjective_diversity_calibrated",
                "subjective_follow_up_calibrated", "subjective_position_calibrated",
                "subjective_count_calibrated",
            }
        ]
        with (output_dir / "paper_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["strategy", "metric", "mean", "stddev", "sample_count"],
            )
            writer.writeheader(); writer.writerows(paper_rows)
        stage = self._stage_for_experiment(experiment)
        trend = verify_paper_conclusions(payload["statistics"])
        complete = len([run for run in experiment.runs if run.status == "completed"]) == len(
            json.loads(experiment.benchmark_queries_json or "[]")
        ) * len(STRATEGY_LABELS) * 5
        subjective_complete = sum(
            1 for run in experiment.runs for metric in run.metrics
            if metric.name == "subjective_impression_calibrated"
        ) == len(experiment.runs)
        trend["fidelity"] = fidelity_scores(
            complete=complete,
            subjective_complete=subjective_complete,
            trend_similarity=trend["trend_similarity"],
        )
        trend["stage"] = stage
        trend["stage_decision"] = stage_decision(stage, trend["trend_similarity"], complete)
        (output_dir / "paper_conclusion_verification.json").write_text(
            json.dumps(trend, indent=2), encoding="utf-8"
        )
        with (output_dir / "paper_conclusion_verification.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "scope", "metric", "claim", "status", "paper_evidence", "experimental_evidence"])
            writer.writeheader()
            for claim in trend["claims"]:
                writer.writerow({
                    "id": claim["id"], "scope": claim["scope"], "metric": claim["metric"],
                    "claim": claim["claim"], "status": claim["status"],
                    "paper_evidence": claim["paper_evidence"],
                    "experimental_evidence": json.dumps(claim.get("evidence") or {"reason": claim.get("reason")}),
                })
        return self._write_report(experiment, payload, trend, output_dir)

    def _write_report(self, experiment, payload, trend, output_dir):
        completed = len([run for run in experiment.runs if run.status == "completed"])
        expected = len(json.loads(experiment.benchmark_queries_json or "[]")) * len(STRATEGY_LABELS) * 5
        subjective_count = sum(
            1 for run in experiment.runs for metric in run.metrics
            if metric.name == "subjective_impression_calibrated"
        )
        complete = completed == expected
        report = (
            "# Princeton GEO Replication Run\n\n"
            f"- Dataset: GEO-Optim/geo-bench test\n- Provider: {experiment.provider}\n"
            f"- Model: {experiment.llm_model}\n- Strategies: {len(STRATEGY_LABELS)}\n"
            f"- Completed samples: {completed}/{expected}\n"
            f"- Subjective samples calibrated: {subjective_count}/{expected}\n"
            f"- Methodological fidelity: {'high' if complete and subjective_count == expected else 'partial'}\n"
            "- Model fidelity: partial (current alias is not the historical checkpoint)\n"
            f"- Result fidelity: {'ready for comparison' if complete else 'not established'}\n"
            f"- Trend fidelity: {'ready for comparison' if complete else 'not established'}\n\n"
            "## Reproducible outputs\n\n"
            "`runs.csv` contains sample-level provenance and metrics; `paper_metrics.csv` "
            "contains strategy-level paper metrics; `paper_objective_metrics.png` reproduces "
            "the objective-method comparison as a PNG. Paper-oriented means and deviations "
            "are expressed on the paper's 0–100 display scale.\n\n"
            "## Published comparison anchors\n\n"
            "Table 1 reports No Optimization PAWC 19.3, Quotation Addition 27.2 and "
            "Statistics Addition 25.2. Numerical agreement must be assessed only after the "
            "full run; current model aliases prevent an exact-checkpoint claim.\n\n"
            "## Known deviations\n\n"
            "The public test split has three rows without Top-5 sources. Subjective scores use "
            "the public GPT-3.5-instruct/logprob procedure when enabled; exact historical model "
            "snapshots and numeric seeds are unavailable.\n\n"
            "## Paper Conclusion Verification\n\n"
            f"Trend similarity: {self._percent(trend['trend_similarity'])}. "
            f"Stage decision: **{trend['stage_decision']['decision']}** "
            f"(threshold {trend['stage_decision']['threshold']:.0%}).\n\n"
            + "\n".join(
                f"- **{claim['status']}** — {claim['claim']} Evidence: "
                f"`{json.dumps(claim.get('evidence') or {'reason': claim.get('reason')})}`"
                for claim in trend["claims"]
            )
            + "\n\n## Replication Confidence\n\n"
            + "\n".join(
                f"- {name.replace('_', ' ').title()}: {self._percent(value)}"
                for name, value in trend["fidelity"].items() if not name.endswith("_note")
            )
            + f"\n- Model Fidelity note: {trend['fidelity']['model_fidelity_note']}\n"
        )
        path = output_dir / "ReplicationReport.md"
        path.write_text(report, encoding="utf-8")
        return path

    def _stage_for_experiment(self, experiment):
        count = len(json.loads(experiment.benchmark_queries_json or "[]"))
        return next((name for name, config in STAGES.items() if config["queries"] == count), "full")

    @staticmethod
    def _percent(value):
        return "Unknown" if value is None else f"{value:.1%}"

    def _calibrate_subjective(self, experiment):
        facets = (
            "relevance", "influence", "uniqueness", "diversity",
            "follow_up", "subjective_position", "subjective_count",
        )
        aligned = []
        for run in experiment.runs:
            metrics = {metric.name: metric.value for metric in run.metrics}
            if metrics.get("pawc") is None or any(
                metrics.get(f"subjective_{facet}") is None for facet in facets
            ):
                continue
            aligned.append((run.id, metrics))
        if not aligned:
            return
        calibrated_by_run = {run_id: {} for run_id, _ in aligned}
        pawc = [metrics["pawc"] for _, metrics in aligned]
        for facet in facets:
            values = calibrate_subjective_scores(
                [metrics[f"subjective_{facet}"] for _, metrics in aligned], pawc
            )
            for (run_id, _), value in zip(aligned, values):
                calibrated_by_run[run_id][f"subjective_{facet}_calibrated"] = value
        for values in calibrated_by_run.values():
            values["subjective_impression_calibrated"] = sum(values.values()) / len(facets)
        self.repository.store_calibrated_subjective_metrics(
            experiment, calibrated_by_run,
        )

    def _documents(self, entry):
        return [RetrievedDocument(
            rank=row["rank"], title=row["title"], url=row["url"],
            plain_text=row["content"],
            is_optimization_target=row.get("is_optimization_target", False),
        ) for row in entry["documents"]]
