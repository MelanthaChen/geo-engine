import csv
import io
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.database import SessionLocal
from app.experiment.campaign_service import ExperimentCampaignService
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
    provider: str | None = Field(default="chatgpt")
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
        provider=request.provider,
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


@router.get("/experiments")
def list_experiments(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    return {"experiments": [
        repository.serialize(experiment)
        for experiment in repository.list_experiments(property_id=property_id)
    ]}


@router.post("/experiments/{experiment_id}/duplicate")
def duplicate_experiment(
    experiment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    source = repository.get_run(experiment_id)
    if not source:
        raise HTTPException(status_code=404, detail="Experiment not found")
    duplicate = repository.create_run(
        property_id=source.property_id,
        name=f"{source.name} (copy)",
        description=source.description,
        llm_model=source.llm_model,
        provider=source.provider,
        dataset_name=source.dataset_name,
        benchmark_queries=json.loads(source.benchmark_queries_json or "[]"),
        strategies=json.loads(source.strategies_json or "[]"),
        metrics=json.loads(source.metrics_json or "[]"),
        number_of_queries=source.number_of_queries,
        random_seed=source.random_seed,
        temperature=source.temperature,
    )
    background_tasks.add_task(execute_experiment_background, duplicate.id)
    return repository.serialize(duplicate)


@router.get("/experiments/{experiment_id}/export.json")
def export_experiment_json(experiment_id: int, db: Session = Depends(get_db)):
    repository = ExperimentRepository(db)
    experiment = repository.get_run(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return repository.serialize(experiment)


@router.get("/experiments/{experiment_id}/export.csv")
def export_experiment_csv(experiment_id: int, db: Session = Depends(get_db)):
    repository = ExperimentRepository(db)
    experiment = repository.get_run(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    rows = repository.experiment_csv_rows(experiment)
    output = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["experiment_id"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="experiment_{experiment_id}.csv"'},
    )


@router.post("/campaigns")
def create_campaign(
    request: ExperimentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    service = ExperimentCampaignService(repository=repository)
    campaign = service.create_campaign(
        property_id=request.property_id,
        name=request.experiment_name,
        description=request.description,
        provider=request.provider,
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
    background_tasks.add_task(execute_campaign_background, campaign.id)

    return repository.serialize_campaign(campaign)


@router.post("/campaigns/{campaign_id}/resume")
def resume_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    campaign = repository.get_campaign(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == "completed":
        return repository.serialize_campaign(campaign)

    background_tasks.add_task(execute_campaign_background, campaign.id)
    return repository.serialize_campaign(campaign)


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    campaign = repository.get_campaign(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return repository.serialize_campaign(campaign)


@router.get("/campaigns/{campaign_id}/export.json")
def export_campaign_json(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    campaign = repository.get_campaign(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return repository.campaign_json_export(campaign)


@router.get("/campaigns/{campaign_id}/export.csv")
def export_campaign_csv(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    repository = ExperimentRepository(db)
    campaign = repository.get_campaign(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    rows = repository.campaign_csv_rows(campaign)
    output = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["campaign_id"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    filename = f"experiment_campaign_{campaign_id}.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def execute_experiment_background(experiment_id: int):
    with SessionLocal() as db:
        repository = ExperimentRepository(db)
        service = ExperimentService(repository=repository)
        service.execute_experiment(experiment_id)


def execute_campaign_background(campaign_id: int):
    with SessionLocal() as db:
        repository = ExperimentRepository(db)
        service = ExperimentCampaignService(repository=repository)
        service.execute_campaign(campaign_id)
