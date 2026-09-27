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
        sample_ids = [sample.sample_id for sample in eligible_samples]
        manifest = {
            "schema_version": "teacher-dataset-manifest-v1",
            "dataset_version": dataset_version,
            "creation_time": creation_time.isoformat(),
            "sample_ids": sample_ids,
            "experiment_ids": sorted({sample.experiment_id for sample in eligible_samples}),
            "teacher_models": sorted({sample.teacher_model for sample in eligible_samples}),
            "metric_versions": sorted({sample.metric_version for sample in eligible_samples}),
        }
        dataset = TeacherDatasetVersion(
            dataset_version=dataset_version,
            creation_time=creation_time,
            teacher_model=", ".join(manifest["teacher_models"]) or "none",
            metric_version=", ".join(manifest["metric_versions"]) or "none",
            experiment_count=len(manifest["experiment_ids"]),
            sample_count=len(eligible_samples),
            manifest_json=canonical_json(manifest),
            manifest_hash=provenance_hash(manifest),
        )
        self.db.add_all([*samples, dataset])
        self.db.flush()
        self.db.add_all([
            TeacherDatasetMember(dataset_version_id=dataset.id, sample_id=sample.sample_id, ordinal=index)
            for index, sample in enumerate(eligible_samples, start=1)
        ])
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    @staticmethod
    def _training_eligible(provenance):
        if "training_eligible" in provenance:
            return bool(provenance["training_eligible"])
        return not any(
            "frozen" in (source.get("retrieval_provider") or "")
            for source in provenance.get("source_set", [])
        )
