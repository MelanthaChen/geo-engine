"""Independent bridge from completed Princeton experiments to research data."""

import json

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


class TeacherPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.builder = TrainingSampleBuilder()
        self.writer = DatasetWriter(db)

    def process_completed_experiments(self) -> dict:
        processed_run_ids = {
            row[0] for row in self.db.query(TeacherTrainingSample.experiment_run_id).all()
        }
        experiments = self._completed_experiments()
        version = self.writer.next_version()
        samples = []
        skipped = []

        for experiment in experiments:
            audit = self._audit_for(experiment)
            for query in experiment.queries:
                baseline_by_index = {
                    run.sample_index: run
                    for run in experiment.runs
                    if run.experiment_query_id == query.id and run.strategy == "original"
                }
                optimized_runs = [
                    run for run in experiment.runs
                    if run.experiment_query_id == query.id
                    and run.strategy != "original"
                    and run.id not in processed_run_ids
                ]
                for optimized_run in optimized_runs:
                    try:
                        samples.append(self.builder.build(
                            experiment=experiment,
                            query=query,
                            baseline_run=baseline_by_index.get(optimized_run.sample_index),
                            optimized_run=optimized_run,
                            audit=audit,
                            dataset_version=version,
                        ))
                    except IncompleteTeacherExperiment as error:
                        skipped.append({"experiment_run_id": optimized_run.id, "reason": str(error)})

        dataset = self.writer.append(samples, version)
        return {
            "dataset_version": dataset.dataset_version if dataset else None,
            "generated_samples": len(samples),
            "skipped": skipped,
        }

    def status(self, *, property_id: int | None = None, recent_limit: int = 10) -> dict:
        sample_query = self.db.query(TeacherTrainingSample)
        experiment_query = self.db.query(Experiment).filter(Experiment.status == "completed")
        if property_id is not None:
            sample_query = sample_query.filter(TeacherTrainingSample.website_id == property_id)
            experiment_query = experiment_query.filter(Experiment.property_id == property_id)

        samples = sample_query.order_by(TeacherTrainingSample.created_at.desc()).all()
        latest_dataset = (
            self.db.query(TeacherDatasetVersion)
            .order_by(TeacherDatasetVersion.creation_time.desc())
            .first()
        )
        processed_experiments = {sample.experiment_id for sample in samples}
        processed_run_ids = {sample.experiment_run_id for sample in samples}
        completed_experiments = experiment_query.options(joinedload(Experiment.runs)).all()
        pending_experiments = sum(
            1
            for experiment in completed_experiments
            if any(
                run.strategy != "original" and run.id not in processed_run_ids
                for run in experiment.runs
            )
        )
        recent = samples[:recent_limit]
        return {
            "module": "teacher_pipeline",
            "status": "ready" if samples else "empty",
            "training_enabled": False,
            "generated_samples": len(samples),
            "processed_experiments": len(processed_experiments),
            "completed_experiments_pending": pending_experiments,
            "teacher_models": sorted({sample.teacher_model for sample in samples}),
            "dataset_version": latest_dataset.dataset_version if latest_dataset else None,
            "last_experiment_processed": recent[0].experiment_id if recent else None,
            "last_processed_at": recent[0].created_at if recent else None,
            "recent_samples": [self.serialize_sample(sample) for sample in recent],
            "dataset": self.serialize_dataset(latest_dataset) if latest_dataset else None,
        }

    def list_samples(self, *, property_id: int | None = None, limit: int = 100):
        query = self.db.query(TeacherTrainingSample)
        if property_id is not None:
            query = query.filter(TeacherTrainingSample.website_id == property_id)
        return [
            self.serialize_sample(sample)
            for sample in query.order_by(TeacherTrainingSample.created_at.desc()).limit(limit).all()
        ]

    def export_latest(self) -> tuple[dict, list[dict]]:
        dataset = self.db.query(TeacherDatasetVersion).order_by(TeacherDatasetVersion.creation_time.desc()).first()
        if dataset is None:
            return {}, []
        samples = (
            self.db.query(TeacherTrainingSample)
            .join(TeacherDatasetMember, TeacherDatasetMember.sample_id == TeacherTrainingSample.sample_id)
            .filter(TeacherDatasetMember.dataset_version_id == dataset.id)
            .order_by(TeacherDatasetMember.ordinal.asc())
            .all()
        )
        return self.serialize_dataset(dataset), [self.serialize_sample(sample) for sample in samples]

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

    def _audit_for(self, experiment):
        if not experiment.property_id:
            return None
        query = self.db.query(WebsiteAudit).filter(
            WebsiteAudit.property_id == experiment.property_id,
            WebsiteAudit.status == "completed",
        )
        if experiment.completed_at:
            query = query.filter(WebsiteAudit.completed_at <= experiment.completed_at)
        return query.order_by(WebsiteAudit.completed_at.desc()).first()

    @staticmethod
    def serialize_sample(sample):
        return {
            "sample_id": sample.sample_id,
            "website_id": sample.website_id,
            "experiment_id": sample.experiment_id,
            "experiment_run_id": sample.experiment_run_id,
            "audit_id": sample.audit_id,
            "audit_version": sample.audit_version,
            "feature_vector": json.loads(sample.feature_vector_json),
            "strategy": sample.strategy,
            "teacher_provider": sample.teacher_provider,
            "teacher_model": sample.teacher_model,
            "teacher_model_version": sample.teacher_model_version,
            "prompt_version": sample.prompt_version,
            "evaluation_version": sample.evaluation_version,
            "original_metrics": json.loads(sample.original_metrics_json),
            "optimized_metrics": json.loads(sample.optimized_metrics_json),
            "delta_metrics": json.loads(sample.delta_metrics_json),
            "provenance": json.loads(sample.provenance_json),
            "dataset_version": sample.dataset_version,
            "provenance_hash": sample.provenance_hash,
            "created_at": sample.created_at,
        }

    @staticmethod
    def serialize_dataset(dataset):
        return {
            "dataset_version": dataset.dataset_version,
            "creation_time": dataset.creation_time,
            "teacher_model": dataset.teacher_model,
            "metric_version": dataset.metric_version,
            "experiment_count": dataset.experiment_count,
            "sample_count": dataset.sample_count,
            "manifest_hash": dataset.manifest_hash,
        }
