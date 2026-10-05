"""Immutable dataset-version writer."""

from datetime import datetime, timezone
import json

from sqlalchemy.orm import Session

from app.teacher_pipeline.models import (
    TeacherDatasetMember,
    TeacherDatasetVersion,
    TeacherTrainingSample,
)
from app.teacher_pipeline.provenance import canonical_json, provenance_hash


class DatasetWriter:
    def __init__(self, db: Session):
        self.db = db

    def next_version(self) -> str:
        latest = self.db.query(TeacherDatasetVersion).count() + 1
        return f"teacher-dataset-v{latest:06d}"

    def append(self, samples, dataset_version: str) -> TeacherDatasetVersion | None:
        if not samples:
            return None
        creation_time = datetime.now(timezone.utc)
        existing_samples = self.db.query(TeacherTrainingSample).all()
        all_samples = [*existing_samples, *samples]
        eligible_samples = [
            sample for sample in all_samples
            if self._training_eligible(json.loads(sample.provenance_json))
        ]
        contexts = self._group_by_context(eligible_samples)
        representatives = [rows[0] for _, rows in contexts]
        sample_ids = [sample.sample_id for sample in representatives]
        manifest = {
            "schema_version": "teacher-dataset-manifest-v2",
            "dataset_version": dataset_version,
            "creation_time": creation_time.isoformat(),
            "sample_ids": sample_ids,
            "contexts": [
                {
                    "context_fingerprint": fingerprint,
                    "representative_sample_id": rows[0].sample_id,
                    "raw_sample_ids": [sample.sample_id for sample in rows],
                }
                for fingerprint, rows in contexts
            ],
            "experiment_ids": sorted({sample.experiment_id for sample in representatives}),
            "teacher_models": sorted({sample.teacher_model for sample in representatives}),
            "metric_versions": sorted({sample.metric_version for sample in representatives}),
        }
        dataset = TeacherDatasetVersion(
            dataset_version=dataset_version,
            creation_time=creation_time,
            teacher_model=", ".join(manifest["teacher_models"]) or "none",
            metric_version=", ".join(manifest["metric_versions"]) or "none",
            experiment_count=len(manifest["experiment_ids"]),
            sample_count=len(representatives),
            manifest_json=canonical_json(manifest),
            manifest_hash=provenance_hash(manifest),
        )
        self.db.add_all([*samples, dataset])
        self.db.flush()
        self.db.add_all([
            TeacherDatasetMember(
                dataset_version_id=dataset.id,
                sample_id=rows[0].sample_id,
                context_fingerprint=fingerprint,
                ordinal=index,
            )
            for index, (fingerprint, rows) in enumerate(contexts, start=1)
        ])
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    @staticmethod
    def _training_eligible(provenance):
        if provenance.get("source_mode") == "frozen_demo":
            return False
        experiment = provenance.get("experiment", {})
        query = provenance.get("query", {})
        target = provenance.get("selected_document", {})
        sources = provenance.get("source_set", [])
        plan = provenance.get("rewrite_plan") or {}
        optimized = provenance.get("optimized_target_content")
        if not experiment.get("completed_at") or not query.get("text"):
            return False
        if not target.get("page_id") or not target.get("url"):
            return False
        if len(sources) != 5 or not any(source.get("is_target") for source in sources):
            return False
        if plan.get("version") != "rewrite-plan-v1" or not plan.get("operations"):
            return False
        if not isinstance(optimized, str) or len(optimized.strip()) < 20:
            return False
        if provenance.get("baseline_answer") is None or provenance.get("treatment_answer") is None:
            return False
        if not provenance.get("aggregate_metrics"):
            return False
        return bool(provenance.get("training_eligible", True))

    @staticmethod
    def _group_by_context(samples):
        grouped = {}
        for sample in samples:
            provenance = json.loads(sample.provenance_json)
            fingerprint = provenance.get("context_fingerprint") or f"legacy:{sample.sample_id}"
            grouped.setdefault(fingerprint, []).append(sample)
        return [
            (fingerprint, sorted(rows, key=lambda sample: (str(sample.created_at or ""), sample.sample_id), reverse=True))
            for fingerprint, rows in sorted(grouped.items())
        ]
