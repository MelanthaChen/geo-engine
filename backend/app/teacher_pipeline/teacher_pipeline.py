"""Independent bridge from completed Princeton experiments to research data."""

import copy
import json
import statistics

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.experiment import Experiment, ExperimentQuery, ExperimentRun
from app.models.website_audit import WebsiteAudit
from app.teacher_pipeline.dataset_writer import DatasetWriter
from app.teacher_pipeline.models import (
    TeacherDatasetMember,
    TeacherDatasetVersion,
    TeacherTrainingSample,
)
from app.teacher_pipeline.sample_builder import IncompleteTeacherExperiment, TrainingSampleBuilder
from app.teacher_pipeline.provenance import context_fingerprint, provenance_hash


class TeacherPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.builder = TrainingSampleBuilder()
        self.writer = DatasetWriter(db)

    def process_completed_experiments(self) -> dict:
        existing_fingerprints = {
            json.loads(row[0]).get("context_fingerprint")
            for row in self.db.query(TeacherTrainingSample.provenance_json).all()
        }
        existing_fingerprints.discard(None)
        experiments = self._completed_experiments()
        version = self.writer.next_version()
        samples = []
        skipped = []

        for experiment in experiments:
            for query in experiment.queries:
                audit = self._audit_for(experiment, query=query)
                baseline_by_index = {
                    run.sample_index: run
                    for run in experiment.runs
                    if run.experiment_query_id == query.id and run.strategy == "original"
                }
                optimized_runs = sorted([
                    run for run in experiment.runs
                    if run.experiment_query_id == query.id
                    and run.strategy != "original"
                ], key=lambda run: (run.strategy, run.sample_index, run.id))
                strategies = sorted({run.strategy for run in optimized_runs})
                for strategy in strategies:
                    strategy_runs = [run for run in optimized_runs if run.strategy == strategy]
                    fingerprint = context_fingerprint(query=query, strategy=strategy)
                    if fingerprint in existing_fingerprints:
                        skipped.append({
                            "experiment_run_ids": [run.id for run in strategy_runs],
                            "reason": "Duplicate query/source-set/strategy context",
                        })
                        continue
                    try:
                        sample = self.builder.build_context(
                            experiment=experiment,
                            query=query,
                            baseline_runs=list(baseline_by_index.values()),
                            optimized_runs=strategy_runs,
                            audit=audit,
                            dataset_version=version,
                        )
                        samples.append(sample)
                        existing_fingerprints.add(fingerprint)
                    except IncompleteTeacherExperiment as error:
                        skipped.append({
                            "experiment_run_ids": [run.id for run in strategy_runs],
                            "reason": str(error),
                        })

        dataset = self.writer.append(samples, version)
        return {
            "dataset_version": dataset.dataset_version if dataset else None,
            "generated_samples": len(samples),
            "unique_training_contexts": len(samples),
            "repetitions": sum(
                json.loads(sample.provenance_json).get("repetition_count", 1)
                for sample in samples
            ),
            "skipped": skipped,
        }

    def status(self, *, property_id: int | None = None, recent_limit: int = 10) -> dict:
        sample_query = self.db.query(TeacherTrainingSample)
        experiment_query = self.db.query(Experiment).filter(Experiment.status == "completed")
        if property_id is not None:
            sample_query = sample_query.filter(TeacherTrainingSample.website_id == property_id)
            experiment_query = experiment_query.filter(Experiment.property_id == property_id)

        samples = sample_query.order_by(TeacherTrainingSample.created_at.desc()).all()
        serialized_samples = self.consolidate_samples([
            self.serialize_sample(sample) for sample in samples
        ])
        eligible_samples = [sample for sample in serialized_samples if sample["training_eligible"]]
        latest_dataset = (
            self.db.query(TeacherDatasetVersion)
            .order_by(TeacherDatasetVersion.creation_time.desc())
            .first()
        )
        processed_experiments = {sample.experiment_id for sample in samples}
        processed_run_ids = set().union(*(
            self._processed_run_ids(sample) for sample in samples
        )) if samples else set()
        completed_experiments = experiment_query.options(joinedload(Experiment.runs)).all()
        pending_experiments = sum(
            1
            for experiment in completed_experiments
            if any(
                run.strategy != "original" and run.id not in processed_run_ids
                for run in experiment.runs
            )
        )
        recent = serialized_samples[:recent_limit]
        latest_generation = (
            self.db.query(Experiment)
            .filter(Experiment.dataset_name == "teacher_training_contexts")
            .order_by(Experiment.created_at.desc())
            .first()
        )
        unique_queries = {sample["query"] for sample in eligible_samples if sample["query"]}
        target_pages = {sample["target_url"] for sample in eligible_samples if sample["target_url"]}
        intents = {sample["query_intent"] for sample in eligible_samples if sample["query_intent"]}
        reference_sets = {
            tuple(sample["reference_snapshot_hashes"])
            for sample in eligible_samples
            if sample["reference_snapshot_hashes"]
        }
        return {
            "module": "teacher_pipeline",
            "status": "ready" if samples else "empty",
            "training_enabled": False,
            "generated_samples": len(eligible_samples),
            "unique_training_contexts": len(eligible_samples),
            "repetitions": sum(sample["repetition_count"] for sample in eligible_samples),
            "generated_answer_pairs": sum(sample["repetition_count"] for sample in eligible_samples),
            "processed_experiments": len(processed_experiments),
            "completed_experiments_pending": pending_experiments,
            "teacher_models": sorted({sample.teacher_model for sample in samples}),
            "dataset_version": latest_dataset.dataset_version if latest_dataset else None,
            "last_experiment_processed": recent[0]["experiment_id"] if recent else None,
            "last_processed_at": recent[0]["created_at"] if recent else None,
            "recent_samples": recent,
            "dataset": self.serialize_dataset(
                latest_dataset,
                sample_count=self._dataset_context_count(latest_dataset),
            ) if latest_dataset else None,
            "unique_queries": len(unique_queries),
            "representative_target_pages": len(target_pages),
            "query_intents_covered": len(intents),
            "strategies_covered": len({sample["strategy"] for sample in eligible_samples}),
            "reference_source_sets": len(reference_sets),
            "generation": self._generation_status(latest_generation, eligible_samples),
        }

    def list_samples(self, *, property_id: int | None = None, limit: int = 100):
        query = self.db.query(TeacherTrainingSample)
        if property_id is not None:
            query = query.filter(TeacherTrainingSample.website_id == property_id)
        return self.consolidate_samples([
            self.serialize_sample(sample)
            for sample in query.order_by(TeacherTrainingSample.created_at.desc()).limit(limit).all()
        ])

    def export_latest(self) -> tuple[dict, list[dict]]:
        dataset = self.db.query(TeacherDatasetVersion).order_by(TeacherDatasetVersion.creation_time.desc()).first()
        if dataset is None:
            return {}, []
        samples = self._dataset_samples(dataset, include_raw=True)
        serialized = self.consolidate_samples([
            self.serialize_sample(sample) for sample in samples
        ])
        eligible = [sample for sample in serialized if sample["training_eligible"]]
        return self.serialize_dataset(dataset, sample_count=len(eligible)), eligible

    def _completed_experiments(self):
        return (
            self.db.query(Experiment)
            .options(
                selectinload(Experiment.queries).selectinload(ExperimentQuery.documents),
                selectinload(Experiment.runs).selectinload(ExperimentRun.prompt_version),
                selectinload(Experiment.runs).selectinload(ExperimentRun.evaluations),
                selectinload(Experiment.runs).selectinload(ExperimentRun.metrics),
            )
            .filter(Experiment.status == "completed")
            .order_by(Experiment.completed_at.asc())
            .all()
        )

    def _dataset_samples(self, dataset, *, include_raw=False):
        if dataset is None:
            return []
        manifest = json.loads(dataset.manifest_json or "{}")
        contexts = manifest.get("contexts", [])
        raw_ids = [
            sample_id
            for context in contexts
            for sample_id in context.get("raw_sample_ids", [])
        ]
        if include_raw and raw_ids:
            rows = self.db.query(TeacherTrainingSample).filter(
                TeacherTrainingSample.sample_id.in_(raw_ids)
            ).all()
            order = {sample_id: index for index, sample_id in enumerate(raw_ids)}
            return sorted(rows, key=lambda row: order.get(row.sample_id, len(order)))
        return (
            self.db.query(TeacherTrainingSample)
            .join(TeacherDatasetMember, TeacherDatasetMember.sample_id == TeacherTrainingSample.sample_id)
            .filter(TeacherDatasetMember.dataset_version_id == dataset.id)
            .order_by(TeacherDatasetMember.ordinal.asc())
            .all()
        )

    def _dataset_context_count(self, dataset):
        rows = self._dataset_samples(dataset, include_raw=True)
        return len(self.consolidate_samples([self.serialize_sample(row) for row in rows]))

    def _audit_for(self, experiment, *, query=None):
        if not experiment.property_id:
            return None
        if query is not None and query.source_audit_id:
            return self.db.query(WebsiteAudit).options(
                selectinload(WebsiteAudit.pages)
            ).filter(
                WebsiteAudit.id == query.source_audit_id,
                WebsiteAudit.property_id == experiment.property_id,
                WebsiteAudit.status == "completed",
            ).first()
        query = self.db.query(WebsiteAudit).options(
            selectinload(WebsiteAudit.pages)
        ).filter(
            WebsiteAudit.property_id == experiment.property_id,
            WebsiteAudit.status == "completed",
        )
        if experiment.completed_at:
            query = query.filter(WebsiteAudit.completed_at <= experiment.completed_at)
        return query.order_by(WebsiteAudit.completed_at.desc()).first()

    @staticmethod
    def serialize_sample(sample):
        provenance = json.loads(sample.provenance_json)
        query = provenance.get("query", {})
        target = provenance.get("selected_document", {})
        source_set = provenance.get("source_set", [])
        references = [source for source in source_set if not source.get("is_target")]
        source_mode = provenance.get("source_mode") or (
            "frozen_demo" if any(
                "frozen" in (source.get("retrieval_provider") or "")
                for source in source_set
            ) else "benchmark" if provenance.get("experiment", {}).get("dataset_name") == "geo_bench"
            else "live_retrieval"
        )
        return {
            "sample_id": sample.sample_id,
            "website_id": sample.website_id,
            "experiment_id": sample.experiment_id,
            "experiment_run_id": sample.experiment_run_id,
            "audit_id": sample.audit_id,
            "audit_version": sample.audit_version,
            "feature_vector": TeacherPipeline._without_legacy_scores(
                json.loads(sample.feature_vector_json)
            ),
            "strategy": sample.strategy,
            "teacher_provider": sample.teacher_provider,
            "teacher_model": sample.teacher_model,
            "teacher_model_version": sample.teacher_model_version,
            "prompt_version": sample.prompt_version,
            "evaluation_version": sample.evaluation_version,
            "original_metrics": json.loads(sample.original_metrics_json),
            "optimized_metrics": json.loads(sample.optimized_metrics_json),
            "delta_metrics": json.loads(sample.delta_metrics_json),
            "baseline_metrics": json.loads(sample.original_metrics_json),
            "treatment_metrics": json.loads(sample.optimized_metrics_json),
            "metric_deltas": json.loads(sample.delta_metrics_json),
            "provenance": provenance,
            "context_fingerprint": provenance.get("context_fingerprint"),
            "query": query.get("text"),
            "query_source": query.get("query_source"),
            "query_intent": query.get("query_intent"),
            "target_url": target.get("url"),
            "target_page_id": target.get("page_id") or query.get("originating_page_id"),
            "originating_page_id": query.get("originating_page_id"),
            "originating_page_url": query.get("originating_page_url") or target.get("url"),
            "target_snapshot_hash": target.get("content_sha256"),
            "reference_urls": [source.get("url") for source in references],
            "reference_snapshot_hashes": [source.get("content_sha256") for source in references],
            "reference_order": [source.get("rank") for source in references],
            "baseline_answer": provenance.get("baseline_answer"),
            "treatment_answer": provenance.get("treatment_answer"),
            "repetitions": provenance.get("repetitions", []),
            "repetition_count": provenance.get("repetition_count", 1),
            "source_mode": source_mode,
            "training_eligible": bool(
                provenance.get("training_eligible", source_mode != "frozen_demo")
            ),
            "dataset_version": sample.dataset_version,
            "provenance_hash": sample.provenance_hash,
            "created_at": sample.created_at,
        }

    @staticmethod
    def consolidate_samples(samples):
        """Return one formal export row per deterministic context fingerprint."""
        grouped = {}
        order = []
        for sample in samples:
            key = sample.get("context_fingerprint") or f"legacy:{sample['sample_id']}"
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(sample)

        consolidated = []
        for key in order:
            rows = grouped[key]
            formal = copy.deepcopy(rows[0])
            repetitions = []
            seen = set()
            for row in rows:
                provenance = row.get("provenance", {})
                nested = provenance.get("repetitions") or [{
                    "repetition_index": len(repetitions),
                    "sample_index": provenance.get("optimized_run", {}).get("sample_index"),
                    "baseline_run_id": provenance.get("baseline_run", {}).get("id"),
                    "treatment_run_id": row.get("experiment_run_id"),
                    "baseline_run": provenance.get("baseline_run"),
                    "treatment_run": provenance.get("optimized_run"),
                    "baseline_answer": row.get("baseline_answer"),
                    "treatment_answer": row.get("treatment_answer"),
                    "original_metrics": row.get("original_metrics", {}),
                    "optimized_metrics": row.get("optimized_metrics", {}),
                    "delta_metrics": row.get("delta_metrics", {}),
                }]
                for repetition in nested:
                    identity = (
                        repetition.get("baseline_run_id"),
                        repetition.get("treatment_run_id"),
                        repetition.get("sample_index"),
                    )
                    if identity in seen:
                        continue
                    seen.add(identity)
                    item = copy.deepcopy(repetition)
                    item["repetition_index"] = len(repetitions)
                    repetitions.append(item)

            aggregate = formal.get("provenance", {}).get("aggregate_metrics", {})
            if not aggregate or len(rows) > 1:
                aggregate = TeacherPipeline._aggregate_repetitions(repetitions)
            formal["original_metrics"] = aggregate.get("original", formal["original_metrics"])
            formal["optimized_metrics"] = aggregate.get("optimized", formal["optimized_metrics"])
            formal["delta_metrics"] = aggregate.get("delta", formal["delta_metrics"])
            formal["baseline_metrics"] = formal["original_metrics"]
            formal["treatment_metrics"] = formal["optimized_metrics"]
            formal["metric_deltas"] = formal["delta_metrics"]
            formal["repetitions"] = repetitions
            formal["repetition_count"] = len(repetitions)
            formal["baseline_answer"] = repetitions[0].get("baseline_answer") if repetitions else None
            formal["treatment_answer"] = repetitions[0].get("treatment_answer") if repetitions else None
            formal["provenance"]["schema_version"] = "teacher-provenance-v2"
            formal["provenance"]["aggregate_metrics"] = aggregate
            formal["provenance"]["repetitions"] = repetitions
            formal["provenance"]["repetition_count"] = len(repetitions)
            formal["provenance_hash"] = provenance_hash(formal["provenance"])
            consolidated.append(formal)
        return consolidated

    @staticmethod
    def _aggregate_repetitions(repetitions):
        result = {}
        for output_name, input_name in (
            ("original", "original_metrics"),
            ("optimized", "optimized_metrics"),
            ("delta", "delta_metrics"),
        ):
            names = {
                name for repetition in repetitions
                for name in repetition.get(input_name, {})
            }
            result[output_name] = {
                name: statistics.fmean(values)
                for name in sorted(names)
                if (values := [
                    repetition.get(input_name, {}).get(name)
                    for repetition in repetitions
                    if isinstance(repetition.get(input_name, {}).get(name), (int, float))
                ])
            }
        result["sample_count"] = {
            "original": len(repetitions),
            "optimized": len(repetitions),
        }
        return result

    @staticmethod
    def _processed_run_ids(sample):
        provenance = json.loads(sample.provenance_json)
        run_ids = {sample.experiment_run_id}
        for repetition in provenance.get("repetitions", []):
            if repetition.get("treatment_run_id") is not None:
                run_ids.add(repetition["treatment_run_id"])
        return run_ids

    @staticmethod
    def _without_legacy_scores(value):
        deprecated = {"authority_score", "brand_clarity", "content_coverage", "faq_presence"}
        if isinstance(value, dict):
            return {
                key: TeacherPipeline._without_legacy_scores(item)
                for key, item in value.items()
                if key not in deprecated
            }
        if isinstance(value, list):
            return [TeacherPipeline._without_legacy_scores(item) for item in value]
        return value

    @staticmethod
    def _generation_status(experiment, eligible_samples):
        if experiment is None:
            return None
        params = json.loads(experiment.generation_params_json or "{}")
        prepared = 0
        benchmark = json.loads(experiment.benchmark_queries_json or "[]")
        if benchmark and all(isinstance(item, dict) and item.get("documents") for item in benchmark):
            prepared = len(benchmark)
        ready = sum(sample["experiment_id"] == experiment.id for sample in eligible_samples)
        preparing = experiment.status == "preparing_contexts"
        return {
            "experiment_id": experiment.id,
            "status": experiment.status,
            "training_sample_count": experiment.total_queries or 0,
            "repetitions_per_context": params.get(
                "repetitions_per_context", params.get("samples_per_strategy", 5)
            ),
            "queries_prepared": experiment.completed_queries if preparing else prepared,
            "experiments_completed": 0 if preparing else experiment.completed_queries or 0,
            "training_samples_ready": ready,
            "current_query": experiment.current_query,
            "error_message": experiment.error_message,
        }

    @staticmethod
    def serialize_dataset(dataset, sample_count=None):
        return {
            "dataset_version": dataset.dataset_version,
            "creation_time": dataset.creation_time,
            "teacher_model": dataset.teacher_model,
            "metric_version": dataset.metric_version,
            "experiment_count": dataset.experiment_count,
            "sample_count": dataset.sample_count if sample_count is None else sample_count,
            "manifest_hash": dataset.manifest_hash,
        }
