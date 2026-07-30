from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.benchmark_service import (
    benchmark_summary,
    create_benchmark,
    create_benchmark_dataset,
    get_benchmark_execution,
    list_benchmark_datasets,
    list_benchmark_executions,
    list_benchmarks,
    run_benchmark,
    serialize_benchmark,
    serialize_dataset,
    serialize_execution,
)


router = APIRouter(
    prefix="/api/v1/benchmarks",
    tags=["Benchmark Framework"],
)


class BenchmarkDatasetCreateRequest(BaseModel):
    name: str
    description: str | None = None
    queries: list[str]
    property_id: int | None = None
    metadata: dict | None = None


class BenchmarkCreateRequest(BaseModel):
    name: str
    dataset_id: int
    description: str | None = None
    property_id: int | None = None
    providers: list[str] | None = None
    metrics: list[str] | None = None


@router.get("/datasets")
def get_datasets(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    return {
        "datasets": [
            serialize_dataset(dataset)
            for dataset in list_benchmark_datasets(
                db,
                property_id=property_id,
            )
        ]
    }


@router.post("/datasets")
def post_dataset(
    request: BenchmarkDatasetCreateRequest,
    db: Session = Depends(get_db),
):
    dataset = create_benchmark_dataset(
        db,
        name=request.name,
        description=request.description,
        queries=request.queries,
        property_id=request.property_id,
        metadata=request.metadata,
    )

    return serialize_dataset(dataset)


@router.get("")
def get_benchmarks(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    return {
        "benchmarks": [
            serialize_benchmark(benchmark)
            for benchmark in list_benchmarks(
                db,
                property_id=property_id,
            )
        ]
    }


@router.post("")
def post_benchmark(
    request: BenchmarkCreateRequest,
    db: Session = Depends(get_db),
):
    benchmark = create_benchmark(
        db,
        name=request.name,
        description=request.description,
        dataset_id=request.dataset_id,
        property_id=request.property_id,
        providers=request.providers,
        metrics=request.metrics,
    )

    return serialize_benchmark(benchmark)


@router.post("/{benchmark_id}/run")
def run_benchmark_route(
    benchmark_id: int,
    db: Session = Depends(get_db),
):
    try:
        execution = run_benchmark(db, benchmark_id=benchmark_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not execution:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    return serialize_execution(execution)


@router.get("/executions")
def get_executions(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    return {
        "executions": [
            serialize_execution(execution)
            for execution in list_benchmark_executions(
                db,
                property_id=property_id,
            )
        ]
    }


@router.get("/executions/{execution_id}")
def get_execution(
    execution_id: int,
    db: Session = Depends(get_db),
):
    execution = get_benchmark_execution(db, execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return serialize_execution(execution)


@router.get("/summary")
def get_summary(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    return benchmark_summary(db, property_id=property_id)
