"""API contracts for the GEO Predictor foundation.

This module is the foundation for a future GEO prediction system. The
responses intentionally distinguish architectural readiness from model
readiness so clients cannot mistake placeholders for trained output.
"""

from typing import Literal

from pydantic import BaseModel, Field


class PredictorComponentStatus(BaseModel):
    name: str
    status: Literal["available", "planned"]
    detail: str


class PredictorStatusResponse(BaseModel):
    module: str = "geo_predictor"
    status: Literal["foundation_ready"] = "foundation_ready"
    model_ready: bool = False
    version: str = "0.1.0"
    components: list[PredictorComponentStatus]


class PredictorDatasetResponse(BaseModel):
    status: Literal["empty", "available"]
    total_samples: int
    valid_samples: int
    invalid_samples: int
    strategies_covered: int
    experiments_included: int
    latest_sample_time: str | None
    samples_by_strategy: dict[str, int]
    samples_by_model: dict[str, int]
    samples_by_provider: dict[str, int]
    samples_by_experiment: dict[str, int]
    missing_fields: dict[str, int]
    source: str = "geo_experiments"
    feature_fields: list[str]
    target_fields: list[str]
    message: str


class PredictorTrainRequest(BaseModel):
    embedding_model: str = "not_configured"
    target_metric: str = "visibility_score"
    validation_split: float = Field(default=0.2, gt=0, lt=1)
    random_seed: int = 42


class PredictorTrainResponse(BaseModel):
    status: Literal["not_implemented"] = "not_implemented"
    job_id: None = None
    accepted_configuration: PredictorTrainRequest
    message: str


class PredictorPredictRequest(BaseModel):
    query: str = Field(min_length=1)
    strategy: str = Field(default="original", min_length=1)
    original_document: str = Field(min_length=1)
    modified_document: str = Field(min_length=1)


class PredictorPredictResponse(BaseModel):
    status: Literal["not_implemented"] = "not_implemented"
    prediction: None = None
    model_version: None = None
    message: str
