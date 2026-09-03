"""FastAPI routes for the GEO Predictor architectural foundation.

This module is the foundation for a future GEO prediction system.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.predictor.predictor_service import PredictorService
from app.predictor.schemas import (
    PredictorDatasetResponse,
    PredictorPredictRequest,
    PredictorPredictResponse,
    PredictorStatusResponse,
    PredictorTrainRequest,
    PredictorTrainResponse,
)
from app.predictor.training_sample_repository import TrainingSampleRepository


router = APIRouter(prefix="/predictor", tags=["GEO Predictor"])


def get_predictor_service(db: Session = Depends(get_db)) -> PredictorService:
    return PredictorService(TrainingSampleRepository(db))


@router.get("/status", response_model=PredictorStatusResponse)
def get_predictor_status(
    service: PredictorService = Depends(get_predictor_service),
) -> PredictorStatusResponse:
    return service.status()


@router.get("/dataset", response_model=PredictorDatasetResponse)
def get_predictor_dataset(
    service: PredictorService = Depends(get_predictor_service),
) -> PredictorDatasetResponse:
    return service.dataset_overview()


@router.get("/dataset/export")
def export_predictor_dataset(
    format: Literal["csv", "jsonl"] = Query(default="csv"),
    service: PredictorService = Depends(get_predictor_service),
) -> Response:
    content = service.export_dataset(format)
    media_type = "text/csv" if format == "csv" else "application/x-ndjson"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="geo_predictor_dataset.{format}"'
            )
        },
    )


@router.post("/train", response_model=PredictorTrainResponse)
def train_predictor(
    request: PredictorTrainRequest,
    service: PredictorService = Depends(get_predictor_service),
) -> PredictorTrainResponse:
    return service.train(request)


@router.post("/predict", response_model=PredictorPredictResponse)
def predict_geo_outcome(
    request: PredictorPredictRequest,
    service: PredictorService = Depends(get_predictor_service),
) -> PredictorPredictResponse:
    return service.predict(request)
