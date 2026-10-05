"""Research-transparent Teacher Pipeline APIs and explicit dataset generation."""

import csv
import io
import json
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db
from app.core.database import SessionLocal
from app.experiment.experiment_service import ExperimentService
from app.ge.geo_rewriter import STRATEGY_LABELS
from app.models.experiment import Experiment
from app.models.website_audit import WebsiteAudit
from app.storage.experiment_repository import ExperimentRepository
from app.teacher_pipeline.query_contexts import AuditQueryContextGenerator, InsufficientQueryContexts
from app.teacher_pipeline.schemas import TeacherPipelineStatusResponse, TeacherSampleResponse
from app.teacher_pipeline.teacher_pipeline import TeacherPipeline
from app.teacher_pipeline.training_context_builder import TrainingContextBuilder


router = APIRouter(prefix="/api/v1/teacher-pipeline", tags=["Teacher Pipeline"])


class DatasetGenerationRequest(BaseModel):
    property_id: int
    audit_id: int
    strategy: str
    training_sample_count: int = Field(default=100, ge=1, le=100)
    repetitions_per_context: int = Field(default=1, ge=1, le=5)
    provider: str = "chatgpt"
    llm: str = "gpt-3.5-turbo"
    random_seed: int = 42
    temperature: float = Field(default=0.7, ge=0, le=2)
    confirmed: bool = False


@router.post("/dataset-generation/preview")
def preview_dataset_generation(
    request: DatasetGenerationRequest,
    db: Session = Depends(get_db),
):
    audit = _generation_audit(db, request.property_id, request.audit_id)
    _validate_treatment_strategy(request.strategy)
    try:
        contexts = AuditQueryContextGenerator().generate(
            audit,
            count=request.training_sample_count,
        )
    except InsufficientQueryContexts as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "training_sample_count": len(contexts),
        "repetitions_per_context": request.repetitions_per_context,
        "unique_queries": len({context.query.lower() for context in contexts}),
        "representative_target_pages": len({context.target_url for context in contexts}),
        "query_intents": sorted({context.query_intent for context in contexts}),
        "strategy": request.strategy,
        "expected_baseline_calls": len(contexts) * request.repetitions_per_context,
        "expected_strategy_rewrite_calls": len(contexts),
        "expected_treatment_calls": len(contexts) * request.repetitions_per_context,
        "expected_teacher_evaluations": len(contexts) * request.repetitions_per_context * 2,
        "pricing_estimate": None,
    }


@router.post("/dataset-generation/start")
def start_dataset_generation(
    request: DatasetGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not request.confirmed:
        raise HTTPException(
            status_code=422,
            detail="Explicit confirmation is required before paid dataset generation.",
        )
    audit = _generation_audit(db, request.property_id, request.audit_id)
    try:
        contexts = AuditQueryContextGenerator().generate(
            audit,
            count=request.training_sample_count,
        )
    except InsufficientQueryContexts as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    repository = ExperimentRepository(db)
    service = ExperimentService(repository)
    _validate_treatment_strategy(request.strategy)
    experiment = repository.create_run(
        property_id=request.property_id,
        name=f"Audit #{request.audit_id} · {len(contexts)} distinct Teacher contexts",
        description=(
            f"Explicit training-data job: {len(contexts)} unique contexts, "
            f"{request.repetitions_per_context} repetition(s) per context."
        ),
        provider=request.provider,
        llm_model=request.llm,
        dataset_name="teacher_training_contexts",
        benchmark_queries=[{
            "query": context.query,
            "context": {
                "query_source": context.query_source,
                "query_intent": context.query_intent,
                "target_url": context.target_url,
                "target_page_id": context.target_page_id,
                "originating_evidence": context.originating_evidence,
            },
        } for context in contexts],
        strategies=["original", request.strategy],
        metrics=["pawc", "citation_count", "visibility_score"],
        number_of_queries=len(contexts),
        random_seed=request.random_seed,
        temperature=request.temperature,
        repetitions_per_context=request.repetitions_per_context,
    )
    background_tasks.add_task(
        prepare_and_execute_dataset_generation,
        experiment.id,
        request.audit_id,
    )
    return repository.serialize(experiment)


def prepare_and_execute_dataset_generation(experiment_id: int, audit_id: int):
    with SessionLocal() as db:
        repository = ExperimentRepository(db)
        experiment = repository.get_run(experiment_id)
        audit = _generation_audit(db, experiment.property_id, audit_id)
        try:
            contexts = AuditQueryContextGenerator().generate(
                audit,
                count=experiment.total_queries,
            )
            experiment.status = "preparing_contexts"
            db.commit()

            def progress(completed, total, query):
                experiment.completed_queries = completed
                experiment.current_query = query
                experiment.estimated_remaining_time = f"{total - completed} source sets to freeze"
                db.commit()

            entries = TrainingContextBuilder().freeze(contexts, audit=audit, on_progress=progress)
            experiment.benchmark_queries_json = json.dumps(entries)
            experiment.completed_queries = 0
            experiment.status = "queued"
            db.commit()
            ExperimentService(repository).execute_experiment(experiment.id)
        except Exception as exc:
            repository.mark_failed(experiment, str(exc))


def _generation_audit(db: Session, property_id: int, audit_id: int):
    audit = (
        db.query(WebsiteAudit)
        .options(joinedload(WebsiteAudit.property), joinedload(WebsiteAudit.pages))
        .filter(
            WebsiteAudit.id == audit_id,
            WebsiteAudit.property_id == property_id,
            WebsiteAudit.status == "completed",
        )
        .first()
    )
    if audit is None:
        raise HTTPException(status_code=422, detail="A completed matching audit is required.")
    return audit


def _validate_treatment_strategy(strategy: str):
    if strategy == "original":
        raise HTTPException(status_code=422, detail="Original is the baseline, not a treatment strategy.")
    if strategy not in STRATEGY_LABELS:
        raise HTTPException(status_code=422, detail=f"Unsupported GEO strategy: {strategy}")


@router.get("/status", response_model=TeacherPipelineStatusResponse)
def get_status(property_id: int | None = None, db: Session = Depends(get_db)):
    return TeacherPipeline(db).status(property_id=property_id)


@router.get("/samples", response_model=list[TeacherSampleResponse])
def get_samples(
    property_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return TeacherPipeline(db).list_samples(property_id=property_id, limit=limit)


@router.get("/dataset/export")
def export_latest_dataset(
    format: Literal["jsonl", "csv"] = Query(default="jsonl"),
    db: Session = Depends(get_db),
):
    metadata, samples = TeacherPipeline(db).export_latest()
    if format == "csv":
        output = io.StringIO()
        fields = list(samples[0]) if samples else [
            "sample_id", "website_id", "experiment_id", "experiment_run_id",
            "audit_id", "audit_version", "feature_vector", "strategy",
            "teacher_provider", "teacher_model", "teacher_model_version",
            "prompt_version", "evaluation_version", "original_metrics",
            "optimized_metrics", "delta_metrics", "baseline_metrics",
            "treatment_metrics", "metric_deltas", "provenance",
            "context_fingerprint", "query", "query_source", "query_intent",
            "target_url", "target_page_id", "originating_page_id",
            "originating_page_url", "target_snapshot_hash",
            "reference_urls", "reference_snapshot_hashes", "reference_order",
            "baseline_answer", "treatment_answer", "repetitions",
            "repetition_count", "source_mode",
            "training_eligible",
            "dataset_version", "provenance_hash", "created_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for sample in samples:
            writer.writerow({
                key: (
                    json.dumps(value, ensure_ascii=False, default=str)
                    if isinstance(value, (dict, list))
                    else value
                )
                for key, value in sample.items()
            })
        version = metadata.get("dataset_version", "empty")
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{version}.csv"'},
        )
    content = "\n".join(
        [json.dumps({"record_type": "dataset_metadata", **metadata}, default=str)]
        + [json.dumps({"record_type": "training_sample", **sample}, default=str) for sample in samples]
    )
    if content:
        content += "\n"
    version = metadata.get("dataset_version", "empty")
    return Response(
        content=content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{version}.jsonl"'},
    )
