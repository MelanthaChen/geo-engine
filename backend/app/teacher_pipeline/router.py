"""Read-only research transparency API for the Teacher Pipeline."""

import csv
import io
import json
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.teacher_pipeline.schemas import TeacherPipelineStatusResponse, TeacherSampleResponse
from app.teacher_pipeline.teacher_pipeline import TeacherPipeline


router = APIRouter(prefix="/api/v1/teacher-pipeline", tags=["Teacher Pipeline"])


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
            "optimized_metrics", "delta_metrics", "provenance",
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
