"""Immutable persistence models for Teacher Pipeline datasets."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.sql import func

from app.core.database import Base


class TeacherTrainingSample(Base):
    __tablename__ = "teacher_training_samples"
    __table_args__ = (
        UniqueConstraint("experiment_run_id", name="uq_teacher_sample_experiment_run"),
    )

    sample_id = Column(String(36), primary_key=True)
    website_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="RESTRICT"), nullable=False, index=True)
    experiment_run_id = Column(Integer, ForeignKey("experiment_runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    baseline_run_id = Column(Integer, ForeignKey("experiment_runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    experiment_query_id = Column(Integer, ForeignKey("experiment_queries.id", ondelete="RESTRICT"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("website_audits.id", ondelete="RESTRICT"), nullable=False, index=True)
    audit_version = Column(String(100), nullable=False)
    feature_vector_json = Column(Text, nullable=False)
    strategy = Column(String(100), nullable=False, index=True)
    teacher_provider = Column(String(100), nullable=False)
    teacher_model = Column(String(255), nullable=False, index=True)
    teacher_model_version = Column(String(255), nullable=False)
    prompt_version = Column(String(100), nullable=False)
    evaluation_version = Column(String(255), nullable=False)
    metric_version = Column(String(255), nullable=False)
    original_metrics_json = Column(Text, nullable=False)
    optimized_metrics_json = Column(Text, nullable=False)
    delta_metrics_json = Column(Text, nullable=False)
    provenance_json = Column(Text, nullable=False)
    provenance_hash = Column(String(64), nullable=False, unique=True, index=True)
    dataset_version = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TeacherDatasetVersion(Base):
    __tablename__ = "teacher_dataset_versions"

    id = Column(Integer, primary_key=True)
    dataset_version = Column(String(100), nullable=False, unique=True, index=True)
    creation_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    teacher_model = Column(String(255), nullable=False)
    metric_version = Column(String(255), nullable=False)
    experiment_count = Column(Integer, nullable=False)
    sample_count = Column(Integer, nullable=False)
    manifest_json = Column(Text, nullable=False)
    manifest_hash = Column(String(64), nullable=False, unique=True)


class TeacherDatasetMember(Base):
    __tablename__ = "teacher_dataset_members"
    __table_args__ = (
        UniqueConstraint("dataset_version_id", "sample_id", name="uq_teacher_dataset_member"),
    )

    id = Column(Integer, primary_key=True)
    dataset_version_id = Column(Integer, ForeignKey("teacher_dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    sample_id = Column(String(36), ForeignKey("teacher_training_samples.sample_id", ondelete="RESTRICT"), nullable=False, index=True)
    ordinal = Column(Integer, nullable=False)


def _prevent_mutation(*_args, **_kwargs):
    raise ValueError("Teacher Pipeline research records are immutable")


for model in (TeacherTrainingSample, TeacherDatasetVersion, TeacherDatasetMember):
    event.listen(model, "before_update", _prevent_mutation)
    event.listen(model, "before_delete", _prevent_mutation)
