"""Application service for the GEO Predictor foundation."""

from app.predictor.schemas import (
    PredictorComponentStatus,
    PredictorDatasetResponse,
    PredictorPredictRequest,
    PredictorPredictResponse,
    PredictorStatusResponse,
    PredictorTrainRequest,
    PredictorTrainResponse,
)
from app.predictor.dataset_builder import DatasetBuilder
from app.predictor.training_sample_repository import TrainingSampleRepository


class PredictorService:
    """Coordinates predictor-facing use cases without implementing ML.

    This module is the foundation for a future GEO prediction system. Future
    implementations can inject dataset, embedding, and trainer collaborators
    here without changing the HTTP or frontend contracts.
    """

    def __init__(self, repository: TrainingSampleRepository):
        self.repository = repository
        self.dataset_builder = DatasetBuilder(repository)

    def status(self) -> PredictorStatusResponse:
        return PredictorStatusResponse(
            components=[
                PredictorComponentStatus(
                    name="dataset_builder",
                    status="available",
                    detail="Interface ready; experiment extraction is planned.",
                ),
                PredictorComponentStatus(
                    name="embedding_service",
                    status="planned",
                    detail="No embedding provider is configured.",
                ),
                PredictorComponentStatus(
                    name="trainer",
                    status="planned",
                    detail="No training implementation is installed.",
                ),
            ]
        )

    def dataset_overview(self) -> PredictorDatasetResponse:
        statistics = self.dataset_builder.statistics()
        sample_count = statistics["total_samples"]
        return PredictorDatasetResponse(
            status="available" if sample_count else "empty",
            **statistics,
            feature_fields=[
                "query",
                "strategy",
                "original_document",
                "modified_document",
                "prompt",
                "generated_answer",
            ],
            target_fields=[
                "visibility_score",
                "citation_count",
                "subjective_score",
                "pawc",
                "word_score",
                "position_score",
            ],
            message=(
                "Training samples are available."
                if sample_count
                else "No training samples have been generated yet."
            ),
        )

    def export_dataset(self, export_format: str) -> str:
        if export_format == "csv":
            return self.dataset_builder.export_csv()
        if export_format == "jsonl":
            return self.dataset_builder.export_jsonl()
        raise ValueError(f"Unsupported dataset export format: {export_format}")

    def train(self, request: PredictorTrainRequest) -> PredictorTrainResponse:
        # TODO: Delegate to Trainer after dataset/version validation is defined.
        return PredictorTrainResponse(
            accepted_configuration=request,
            message="Training is not implemented; configuration was validated only.",
        )

    def predict(self, request: PredictorPredictRequest) -> PredictorPredictResponse:
        # TODO: Load a versioned artifact and return calibrated GEO estimates.
        del request
        return PredictorPredictResponse(
            message="Prediction is not implemented; no model has been trained.",
        )
