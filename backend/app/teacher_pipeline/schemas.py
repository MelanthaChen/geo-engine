"""Public schemas for research-transparent Teacher Pipeline status."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class TeacherSampleResponse(BaseModel):
    sample_id: str
    website_id: int | None
    experiment_id: int
    experiment_run_id: int
    audit_id: int
    audit_version: str
    feature_vector: dict[str, Any]
    strategy: str
    teacher_provider: str
    teacher_model: str
    teacher_model_version: str
    prompt_version: str
    evaluation_version: str
    original_metrics: dict[str, float | None]
    optimized_metrics: dict[str, float | None]
    delta_metrics: dict[str, float | None]
    baseline_metrics: dict[str, float | None]
    treatment_metrics: dict[str, float | None]
    metric_deltas: dict[str, float | None]
    provenance: dict[str, Any]
    context_fingerprint: str | None
    query: str | None
    query_source: str | None
    query_intent: str | None
    target_url: str | None
    target_page_id: int | None
    target_snapshot_hash: str | None
    reference_urls: list[str | None]
    reference_snapshot_hashes: list[str | None]
    reference_order: list[int | None]
    baseline_answer: str | None
    treatment_answer: str | None
    source_mode: str
    training_eligible: bool
    dataset_version: str
    provenance_hash: str
    created_at: datetime


class DatasetVersionResponse(BaseModel):
    dataset_version: str
    creation_time: datetime
    teacher_model: str
    metric_version: str
    experiment_count: int
    sample_count: int
    manifest_hash: str


class TeacherPipelineStatusResponse(BaseModel):
    module: str = "teacher_pipeline"
    status: Literal["ready", "empty"]
    training_enabled: bool = False
    generated_samples: int
    processed_experiments: int
    completed_experiments_pending: int
    teacher_models: list[str]
    dataset_version: str | None
    last_experiment_processed: int | None
    last_processed_at: datetime | None
    recent_samples: list[TeacherSampleResponse]
    dataset: DatasetVersionResponse | None
    unique_queries: int
    representative_target_pages: int
    query_intents_covered: int
    strategies_covered: int
    reference_source_sets: int
    generation: dict[str, Any] | None
