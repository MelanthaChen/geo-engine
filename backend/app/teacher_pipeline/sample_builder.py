"""Build immutable baseline/treatment samples from completed experiments."""

import uuid
import statistics

from app.services.website_audit.profile import build_website_features, build_website_profile
from app.teacher_pipeline.models import TeacherTrainingSample
from app.teacher_pipeline.provenance import build_provenance, canonical_json, provenance_hash


class IncompleteTeacherExperiment(ValueError):
    pass


class TrainingSampleBuilder:
    metric_schema_version = "princeton-evaluation-metrics-v1"

    def build(self, *, experiment, query, baseline_run, optimized_run, audit, dataset_version):
        self._validate(experiment, query, baseline_run, optimized_run, audit)
        selected_document = next((document for document in query.documents if document.is_selected), None)
        if selected_document is None:
            raise IncompleteTeacherExperiment("Selected source document is missing")

        profile = build_website_profile(audit)
        profile.pop("_evidence", None)
        feature_vector = {
            "schema_version": "website-feature-vector-v1",
            "profile": profile,
            "features": build_website_features(audit),
        }
        original_metrics = self._metrics(baseline_run)
        optimized_metrics = self._metrics(optimized_run)
        metric_names = sorted(set(original_metrics) | set(optimized_metrics))
        delta_metrics = {
            name: self._delta(original_metrics.get(name), optimized_metrics.get(name))
            for name in metric_names
        }
        aggregate_metrics = self._aggregate_metrics(query, optimized_run.strategy)
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
