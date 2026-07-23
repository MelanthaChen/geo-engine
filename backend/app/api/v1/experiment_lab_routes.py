from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.database import SessionLocal
from app.experiment.experiment_service import ExperimentService
from app.storage.experiment_repository import ExperimentRepository


router = APIRouter(
    prefix="/api/v1/experiment-lab",
    tags=["Experiment Lab"],
)


class UploadedDatasetDocument(BaseModel):
    query: str = Field(min_length=1)
    rank: int = Field(ge=1)
    title: str | None = None
    url: str = Field(default="")
    content: str = Field(min_length=1)


class ExperimentRunRequest(BaseModel):
    property_id: int | None = None
    experiment_name: str = Field(default="Princeton GEO Reproduction")
    description: str | None = None
    llm: str = Field(default="gpt-3.5-turbo")
    dataset: str = Field(default="custom")
    queries: list[str] | None = None
    dataset_documents: list[UploadedDatasetDocument] | None = None
    strategies: list[str]
    number_of_queries: int = Field(default=1, ge=1)
    random_seed: int = Field(default=42)
    temperature: float = Field(default=0.7, ge=0, le=2)
    evaluation_metrics: list[str]


@router.post("/run")
def run_experiment(
    request: ExperimentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    service = ExperimentService(repository=repository)
    experiment = service.create_experiment(
        property_id=request.property_id,
        name=request.experiment_name,
        description=request.description,
        llm_model=request.llm,
        dataset_name=request.dataset,
        queries=request.queries,
        dataset_documents=(
            [
                document.model_dump()
                for document in request.dataset_documents
            ]
            if request.dataset_documents
            else None
        ),
        strategies=request.strategies,
        metrics=request.evaluation_metrics,
        number_of_queries=request.number_of_queries,
        random_seed=request.random_seed,
        temperature=request.temperature,
    )
    background_tasks.add_task(execute_experiment_background, experiment.id)

    return repository.serialize(experiment)


@router.get("/runs/{experiment_id}")
def get_experiment_run(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    experiment = repository.get_run(experiment_id)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return repository.serialize(experiment)


def execute_experiment_background(experiment_id: int):
    with SessionLocal() as db:
        repository = ExperimentRepository(db)
        service = ExperimentService(repository=repository)
        service.execute_experiment(experiment_id)
