"""Build immutable baseline/treatment samples from completed experiments."""

import json
import uuid
import statistics

from app.teacher_pipeline.models import TeacherTrainingSample
from app.teacher_pipeline.provenance import (
    build_provenance,
    canonical_json,
    provenance_hash,
    run_provenance,
)


class IncompleteTeacherExperiment(ValueError):
    pass


class TrainingSampleBuilder:
    metric_schema_version = "princeton-evaluation-metrics-v1"

    def build(self, *, experiment, query, baseline_run, optimized_run, audit, dataset_version):
        return self.build_context(
            experiment=experiment,
            query=query,
            baseline_runs=[baseline_run],
            optimized_runs=[optimized_run],
            audit=audit,
            dataset_version=dataset_version,
        )

    def build_context(
        self,
        *,
        experiment,
        query,
        baseline_runs,
        optimized_runs,
        audit,
        dataset_version,
    ):
        """Build one formal sample from every repetition of one fixed context."""
        baseline_by_index = {run.sample_index: run for run in baseline_runs if run is not None}
        pairs = [
            (baseline_by_index.get(run.sample_index), run)
            for run in sorted(
                (item for item in optimized_runs if item is not None),
                key=lambda item: (item.sample_index, item.id),
            )
        ]
        if not pairs:
            raise IncompleteTeacherExperiment("At least one treatment repetition is required")
        for baseline_run, optimized_run in pairs:
            self._validate(experiment, query, baseline_run, optimized_run, audit)

        baseline_run, optimized_run = pairs[0]
        selected_document = next((document for document in query.documents if document.is_selected), None)
        if selected_document is None:
            raise IncompleteTeacherExperiment("Selected source document is missing")

        rewritten_documents = {
            run.strategy_result.modified_document_text
            for _, run in pairs
            if run.strategy_result is not None
        }
        if len(rewritten_documents) != 1:
            raise IncompleteTeacherExperiment(
                "All repetitions must use one identical rewritten target document"
            )

        feature_vector = self._factual_feature_vector(audit)
        aggregate_metrics = self._aggregate_metrics(query, optimized_run.strategy)
        original_metrics = aggregate_metrics["original"]
        optimized_metrics = aggregate_metrics["optimized"]
        delta_metrics = aggregate_metrics["delta"]
        evaluation_version = self._evaluation_version(optimized_run)
        provenance = build_provenance(
            experiment=experiment,
            query=query,
            baseline_run=baseline_run,
            optimized_run=optimized_run,
            audit=audit,
            selected_document=selected_document,
            aggregate_metrics=aggregate_metrics,
        )
        provenance["schema_version"] = "teacher-provenance-v2"
        provenance["repetitions"] = [
            self._repetition(index, baseline, treatment)
            for index, (baseline, treatment) in enumerate(pairs)
        ]
        provenance["repetition_count"] = len(pairs)
        provenance["feature_vector_schema"] = feature_vector["schema_version"]
        provenance["metric_schema_version"] = self.metric_schema_version
        provenance["primary_training_label"] = {
            "name": "aggregate_delta_visibility_score",
            "value": aggregate_metrics["delta"].get("visibility_score"),
        }

        return TeacherTrainingSample(
            sample_id=str(uuid.uuid4()),
            website_id=experiment.property_id,
            experiment_id=experiment.id,
            experiment_run_id=optimized_run.id,
            baseline_run_id=baseline_run.id,
            experiment_query_id=query.id,
            audit_id=audit.id,
            audit_version="website-audit-schema-v1",
            feature_vector_json=canonical_json(feature_vector),
            strategy=optimized_run.strategy,
            teacher_provider=optimized_run.provider,
            teacher_model=optimized_run.model,
            teacher_model_version=optimized_run.model,
            prompt_version=optimized_run.prompt_version.version,
            evaluation_version=evaluation_version,
            metric_version=self.metric_schema_version,
            original_metrics_json=canonical_json(original_metrics),
            optimized_metrics_json=canonical_json(optimized_metrics),
            delta_metrics_json=canonical_json(delta_metrics),
            provenance_json=canonical_json(provenance),
            provenance_hash=provenance_hash(provenance),
            dataset_version=dataset_version,
        )

    def _repetition(self, repetition_index, baseline_run, optimized_run):
        original = self._metrics(baseline_run)
        optimized = self._metrics(optimized_run)
        names = sorted(set(original) | set(optimized))
        return {
            "repetition_index": repetition_index,
            "sample_index": optimized_run.sample_index,
            "baseline_run_id": baseline_run.id,
            "treatment_run_id": optimized_run.id,
            "baseline_run": run_provenance(baseline_run),
            "treatment_run": run_provenance(optimized_run),
            "baseline_answer": baseline_run.raw_response,
            "treatment_answer": optimized_run.raw_response,
            "original_metrics": original,
            "optimized_metrics": optimized,
            "delta_metrics": {
                name: self._delta(original.get(name), optimized.get(name))
                for name in names
            },
        }

    @staticmethod
    def _factual_feature_vector(audit):
        pages = [
            page for page in (getattr(audit, "pages", []) or [])
            if 200 <= (getattr(page, "status_code", 0) or 0) < 300
            and not getattr(page, "is_duplicate", False)
            and (getattr(page, "word_count", 0) or 0) > 0
        ]
        evidence_rows = []
        for page in pages:
            evidence = getattr(page, "evidence_json", None) or {}
            if isinstance(evidence, str):
                try:
                    evidence = json.loads(evidence)
                except json.JSONDecodeError:
                    evidence = {}
            evidence_rows.append(evidence)

        def total(path, fallback=None):
            result = 0
            for page, evidence in zip(pages, evidence_rows):
                value = evidence
                for part in path:
                    value = value.get(part, {}) if isinstance(value, dict) else {}
                if not isinstance(value, (int, float)) and fallback:
                    value = getattr(page, fallback, 0)
                result += value if isinstance(value, (int, float)) else 0
            return result

        def average(path):
            values = []
            for evidence in evidence_rows:
                value = evidence
                for part in path:
                    value = value.get(part, {}) if isinstance(value, dict) else {}
                if isinstance(value, (int, float)):
                    values.append(value)
            return statistics.fmean(values) if values else None

        schema_types = sorted({
            schema
            for page, evidence in zip(pages, evidence_rows)
            for schema in (
                evidence.get("structured_data", {}).get("schema_types")
                or getattr(page, "schema_types", None)
                or []
            )
        })
        word_counts = [getattr(page, "word_count", 0) or 0 for page in pages]
        return {
            "schema_version": "website-factual-evidence-vector-v2",
            "analyzed_page_count": len(pages),
            "total_word_count": sum(word_counts),
            "average_word_count": statistics.fmean(word_counts) if word_counts else 0,
            "pages_with_h1": sum(bool(getattr(page, "h1", None)) for page in pages),
            "pages_with_meta": sum(bool(getattr(page, "meta_description", None)) for page in pages),
            "pages_with_authors": sum(bool(row.get("authorship", {}).get("author_name")) for row in evidence_rows),
            "pages_with_dates": sum(bool(row.get("authorship", {}).get("published_date") or row.get("authorship", {}).get("modified_date")) for row in evidence_rows),
            "internal_link_count": sum(getattr(page, "internal_link_count", 0) or 0 for page in pages),
            "external_link_count": sum(getattr(page, "external_link_count", 0) or 0 for page in pages),
            "reference_like_link_count": total(("strategies", "citation", "reference_like_link_count")),
            "citation_attribution_phrase_count": total(("strategies", "citation", "attribution_phrase_count")),
            "faq_page_schema_count": sum(bool(getattr(page, "faq_page_schema_detected", False)) for page in pages),
            "question_heading_count": sum(getattr(page, "question_heading_count", 0) or 0 for page in pages),
            "qa_pair_count": sum(getattr(page, "detected_qa_pair_count", 0) or 0 for page in pages),
            "quantitative_statement_count": total(("strategies", "statistics", "numeric_claim_count")),
            "blockquote_count": total(("strategies", "quotation", "blockquote_count")),
            "h2_count": sum(getattr(page, "h2_count", 0) or 0 for page in pages),
            "h3_count": sum(getattr(page, "h3_count", 0) or 0 for page in pages),
            "structured_data_types": schema_types,
            "readability_structural_evidence": {
                "sentence_count": total(("strategies", "easy_to_understand", "sentence_count")),
                "paragraph_count": total(("content", "paragraph_count")),
                "list_count": total(("content", "list_count")),
                "average_sentence_words": average(("strategies", "easy_to_understand", "average_sentence_words")),
                "average_paragraph_words": average(("strategies", "easy_to_understand", "average_paragraph_words")),
                "headings_per_100_words": average(("strategies", "easy_to_understand", "headings_per_100_words")),
            },
        }

    def _validate(self, experiment, query, baseline_run, optimized_run, audit):
        if experiment.status != "completed" or not experiment.completed_at:
            raise IncompleteTeacherExperiment("Experiment is not complete")
        if not experiment.property_id or audit is None:
            raise IncompleteTeacherExperiment("A completed website audit is required")
        for run, role in ((baseline_run, "baseline"), (optimized_run, "optimized")):
            if run is None or run.status != "completed" or not run.raw_response:
                raise IncompleteTeacherExperiment(f"Completed {role} run is required")
            if not run.prompt_version or not run.evaluations or not run.metrics:
                raise IncompleteTeacherExperiment(f"{role.title()} prompt, evaluation, or metrics are incomplete")
        if baseline_run.strategy != "original" or optimized_run.strategy == "original":
            raise IncompleteTeacherExperiment("Sample must pair original and optimized strategies")
        if baseline_run.experiment_query_id != query.id or optimized_run.experiment_query_id != query.id:
            raise IncompleteTeacherExperiment("Runs do not belong to the same experiment query")
        if baseline_run.sample_index != optimized_run.sample_index:
            raise IncompleteTeacherExperiment("Baseline and optimized sample indices do not match")
        if baseline_run.provider != optimized_run.provider or baseline_run.model != optimized_run.model:
            raise IncompleteTeacherExperiment("Baseline and optimized teacher contexts do not match")
        if experiment.dataset_name == "new_website_teacher_validation":
            target = next((document for document in query.documents if document.is_selected), None)
            if target is None or target.rank != 1 or target.source_role != "audited_target":
                raise IncompleteTeacherExperiment(
                    "New-website validation target must be the audited page at source rank 1"
                )
            references = [d for d in query.documents if d.source_role == "reference"]
            if len(query.documents) != 5 or len(references) != 4:
                raise IncompleteTeacherExperiment(
                    "New-website validation requires one audited target and four references"
                )

    @staticmethod
    def _aggregate_metrics(query, optimized_strategy):
        grouped = {"original": {}, "optimized": {}}
        for run in query.strategy_results:
            role = "original" if run.strategy == "original" else (
                "optimized" if run.strategy == optimized_strategy else None
            )
            if role is None:
                continue
            values = {
                "word_count": run.word_count,
                "position": run.position,
                "pawc": run.pawc,
                "citation_count": run.citation_count,
                "visibility_score": run.visibility_score,
            }
            for name, value in values.items():
                if value is not None:
                    grouped[role].setdefault(name, []).append(float(value))
        original = {name: statistics.fmean(values) for name, values in grouped["original"].items()}
        optimized = {name: statistics.fmean(values) for name, values in grouped["optimized"].items()}
        delta = {
            name: optimized[name] - original[name]
            for name in sorted(set(original) & set(optimized))
        }
        return {
            "sample_count": {
                "original": len(next(iter(grouped["original"].values()), [])),
                "optimized": len(next(iter(grouped["optimized"].values()), [])),
            },
            "original": original,
            "optimized": optimized,
            "delta": delta,
        }

    @staticmethod
    def _metrics(run):
        return {metric.name: metric.value for metric in run.metrics}

    @staticmethod
    def _delta(original, optimized):
        if original is None or optimized is None:
            return None
        return float(optimized) - float(original)

    @staticmethod
    def _evaluation_version(run):
        return "+".join(sorted(
            f"{evaluation.evaluator}:{evaluation.evaluator_version}"
            for evaluation in run.evaluations
        ))
