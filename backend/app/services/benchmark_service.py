from datetime import datetime, timezone
import hashlib
import json
import time

from sqlalchemy.orm import Session

from app.core.llm_provider import normalize_llm_provider
from app.models.benchmark import (
    Benchmark,
    BenchmarkDataset,
    BenchmarkDatasetQuery,
    BenchmarkExecution,
    BenchmarkResult,
)
from app.repositories.history_repository import create_history_event
from app.services.citation_test_service import execute_prompt_model
from app.services.property_service import get_property


DEFAULT_BENCHMARK_METRICS = [
    "brand_mention_rate",
    "average_position",
    "coverage",
    "latency",
    "response_length",
]


def create_benchmark_dataset(
    db: Session,
    *,
    name: str,
    queries: list[str],
    property_id: int | None = None,
    description: str | None = None,
    metadata: dict | None = None,
):
    cleaned_queries = [query.strip() for query in queries if query.strip()]
    checksum = hashlib.sha256("\n".join(cleaned_queries).encode("utf-8")).hexdigest()
    dataset = BenchmarkDataset(
        property_id=property_id,
        name=name,
        description=description,
        metadata_json=json.dumps(metadata or {}),
        dataset_type=(metadata or {}).get("dataset_type", "question_set"),
        version=str((metadata or {}).get("version", "1")),
        checksum=checksum,
        is_frozen=1,
    )
    db.add(dataset)
    db.flush()

    for index, query_text in enumerate(cleaned_queries, start=1):
        cleaned_query = query_text.strip()

        if not cleaned_query:
            continue

        db.add(
            BenchmarkDatasetQuery(
                dataset_id=dataset.id,
                query_text=cleaned_query,
                rank=index,
                metadata_json=json.dumps({}),
            )
        )

    db.commit()
    db.refresh(dataset)

    return dataset


def list_benchmark_datasets(
    db: Session,
    *,
    property_id: int | None = None,
):
    query = db.query(BenchmarkDataset)

    if property_id is not None:
        query = query.filter(
            (BenchmarkDataset.property_id == property_id)
            | (BenchmarkDataset.property_id.is_(None))
        )

    return query.order_by(BenchmarkDataset.created_at.desc()).all()


def create_benchmark(
    db: Session,
    *,
    name: str,
    dataset_id: int,
    property_id: int | None = None,
    description: str | None = None,
    providers: list[str] | None = None,
    metrics: list[str] | None = None,
):
    normalized_providers = [
        normalize_llm_provider(provider)
        for provider in (providers or ["chatgpt"])
    ]
    selected_metrics = metrics or DEFAULT_BENCHMARK_METRICS

    benchmark = Benchmark(
        property_id=property_id,
        dataset_id=dataset_id,
        name=name,
        description=description,
        providers_json=json.dumps(normalized_providers),
        metrics_json=json.dumps(selected_metrics),
        status="draft",
    )
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)

    return benchmark


def list_benchmarks(
    db: Session,
    *,
    property_id: int | None = None,
):
    query = db.query(Benchmark)

    if property_id is not None:
        query = query.filter(Benchmark.property_id == property_id)

    return query.order_by(Benchmark.created_at.desc()).all()


def run_benchmark(
    db: Session,
    *,
    benchmark_id: int,
):
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()

    if not benchmark:
        return None

    dataset = benchmark.dataset

    if not dataset:
        benchmark.status = "failed"
        db.commit()
        raise ValueError("Benchmark has no dataset.")

    providers = json.loads(benchmark.providers_json or "[\"chatgpt\"]")
    normalized_provider = normalize_llm_provider(providers[0] if providers else None)
    dataset_queries = sorted(dataset.queries, key=lambda item: item.rank)
    property_record = (
        get_property(db, benchmark.property_id)
        if benchmark.property_id is not None
        else None
    )
    target_brand = (
        property_record.brand_name
        if property_record and property_record.brand_name
        else property_record.name if property_record else None
    )
    domain = property_record.domain if property_record else ""

    execution = BenchmarkExecution(
        benchmark_id=benchmark.id,
        property_id=benchmark.property_id,
        dataset_id=dataset.id,
        provider=normalized_provider,
        status="running",
        query_count=len(dataset_queries),
        completed_count=0,
        failed_count=0,
        started_at=datetime.now(timezone.utc),
    )
    benchmark.status = "running"
    db.add(execution)
    db.commit()
    db.refresh(execution)

    create_history_event(
        db=db,
        event_type="benchmark_started",
        property_id=benchmark.property_id,
        benchmark_execution_id=execution.id,
        summary=f"Benchmark started: {benchmark.name}",
        metadata_json=json.dumps(
            {
                "benchmark_id": benchmark.id,
                "dataset_id": dataset.id,
                "provider": normalized_provider,
            }
        ),
    )

    for dataset_query in dataset_queries:
        started_at = time.perf_counter()

        try:
            result = execute_prompt_model(
                prompt=dataset_query.query_text,
                model_name=normalized_provider,
                target_brand=target_brand or "",
                domain=domain,
                provider=normalized_provider,
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            raw_response = result.get("raw_response") or ""
            mentioned = bool(result.get("mentioned"))
            rank = result.get("rank")
            # A brand mention is not evidence of a citation. These legacy
            # columns remain neutral; only directly observed metrics are
            # exposed in metrics_json.
            citation_count = 0
            visibility_score = 0

            db.add(
                BenchmarkResult(
                    execution_id=execution.id,
                    dataset_query_id=dataset_query.id,
                    provider=normalized_provider,
                    query_text=dataset_query.query_text,
                    status=result.get("status") or "finished",
                    latency_ms=latency_ms,
                    mentioned=1 if mentioned else 0,
                    rank=rank,
                    recommendation_found=1 if mentioned else 0,
                    citation_count=citation_count,
                    visibility_score=visibility_score,
                    response_length=len(raw_response),
                    response_snippet=result.get("response_snippet"),
                    raw_response=raw_response,
                    metrics_json=json.dumps(
                        {
                            "brand_mention_rate": 1 if mentioned else 0,
                            "average_position": rank,
                            "coverage": 1,
                            "latency": latency_ms,
                            "response_length": len(raw_response),
                        }
                    ),
                    error_message=result.get("error_message"),
                )
            )
            execution.completed_count += 1
        except Exception as error:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            db.add(
                BenchmarkResult(
                    execution_id=execution.id,
                    dataset_query_id=dataset_query.id,
                    provider=normalized_provider,
                    query_text=dataset_query.query_text,
                    status="failed",
                    latency_ms=latency_ms,
                    metrics_json=json.dumps({"coverage": 0}),
                    error_message=str(error),
                )
            )
            execution.failed_count += 1

        db.commit()

    metrics = aggregate_execution_metrics(execution.results)
    execution.status = "completed" if execution.failed_count == 0 else "failed"
    execution.metrics_json = json.dumps(metrics)
    execution.finished_at = datetime.now(timezone.utc)
    benchmark.status = execution.status
    benchmark.metrics_json = json.dumps(metrics)
    db.commit()
    db.refresh(execution)

    create_history_event(
        db=db,
        event_type="benchmark_completed",
        property_id=benchmark.property_id,
        benchmark_execution_id=execution.id,
        status=execution.status,
        summary=f"Benchmark completed: {benchmark.name}",
        metadata_json=json.dumps(metrics),
    )

    return execution


def get_benchmark_execution(db: Session, execution_id: int):
    return (
        db.query(BenchmarkExecution)
        .filter(BenchmarkExecution.id == execution_id)
        .first()
    )


def list_benchmark_executions(
    db: Session,
    *,
    property_id: int | None = None,
    limit: int = 50,
):
    query = db.query(BenchmarkExecution)

    if property_id is not None:
        query = query.filter(BenchmarkExecution.property_id == property_id)

    return (
        query.order_by(BenchmarkExecution.created_at.desc())
        .limit(limit)
        .all()
    )


def benchmark_summary(
    db: Session,
    *,
    property_id: int | None = None,
):
    execution_query = db.query(BenchmarkExecution)
    dataset_query = db.query(BenchmarkDataset)

    if property_id is not None:
        execution_query = execution_query.filter(
            BenchmarkExecution.property_id == property_id
        )
        dataset_query = dataset_query.filter(
            (BenchmarkDataset.property_id == property_id)
            | (BenchmarkDataset.property_id.is_(None))
        )

    executions = execution_query.all()
    latest_execution = (
        execution_query.order_by(BenchmarkExecution.created_at.desc()).first()
    )
    completed_executions = [
        execution
        for execution in executions
        if execution.status == "completed"
    ]

    latest_metrics = parse_json(latest_execution.metrics_json, {}) if latest_execution else {}

    return {
        "dataset_count": dataset_query.count(),
        "execution_count": len(executions),
        "completed_execution_count": len(completed_executions),
        "latest_execution": serialize_execution(latest_execution)
        if latest_execution
        else None,
        "latest_metrics": latest_metrics,
    }


def aggregate_execution_metrics(results):
    total = len(results)

    if total == 0:
        return {
            "brand_mention_rate": 0,
            "average_position": None,
            "coverage": 0,
            "latency": 0,
            "response_length": 0,
        }

    successful = [result for result in results if result.status == "finished"]
    ranked = [result.rank for result in results if result.rank is not None]

    return {
        "brand_mention_rate": safe_ratio(
            sum(result.mentioned for result in results),
            total,
        ),
        "average_position": (
            sum(ranked) / len(ranked)
            if ranked
            else None
        ),
        "coverage": safe_ratio(len(successful), total),
        "latency": safe_average(
            [
                result.latency_ms
                for result in results
                if result.latency_ms is not None
            ]
        ),
        "response_length": safe_average(
            [result.response_length for result in results]
        ),
    }


def safe_ratio(numerator: int, denominator: int):
    if denominator == 0:
        return 0

    return numerator / denominator


def safe_average(values):
    cleaned = [value for value in values if value is not None]

    if not cleaned:
        return 0

    return sum(cleaned) / len(cleaned)


def serialize_dataset(dataset: BenchmarkDataset):
    return {
        "id": dataset.id,
        "property_id": dataset.property_id,
        "name": dataset.name,
        "description": dataset.description,
        "metadata": parse_json(dataset.metadata_json, {}),
        "query_count": len(dataset.queries),
        "queries": [
            {
                "id": query.id,
                "query_text": query.query_text,
                "rank": query.rank,
                "metadata": parse_json(query.metadata_json, {}),
            }
            for query in sorted(dataset.queries, key=lambda item: item.rank)
        ],
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
    }


def serialize_benchmark(benchmark: Benchmark):
    return {
        "id": benchmark.id,
        "property_id": benchmark.property_id,
        "dataset_id": benchmark.dataset_id,
        "name": benchmark.name,
        "description": benchmark.description,
        "providers": parse_json(benchmark.providers_json, ["chatgpt"]),
        "metrics": parse_json(benchmark.metrics_json, DEFAULT_BENCHMARK_METRICS),
        "status": benchmark.status,
        "execution_count": len(benchmark.executions),
        "created_at": benchmark.created_at,
        "updated_at": benchmark.updated_at,
    }


def serialize_execution(execution: BenchmarkExecution | None):
    if not execution:
        return None

    return {
        "id": execution.id,
        "benchmark_id": execution.benchmark_id,
        "property_id": execution.property_id,
        "dataset_id": execution.dataset_id,
        "provider": execution.provider,
        "status": execution.status,
        "query_count": execution.query_count,
        "completed_count": execution.completed_count,
        "failed_count": execution.failed_count,
        "metrics": parse_json(execution.metrics_json, {}),
        "started_at": execution.started_at,
        "finished_at": execution.finished_at,
        "created_at": execution.created_at,
        "updated_at": execution.updated_at,
        "benchmark": (
            {
                "id": execution.benchmark.id,
                "name": execution.benchmark.name,
                "description": execution.benchmark.description,
            }
            if execution.benchmark
            else None
        ),
        "results": [
            serialize_result(result)
            for result in sorted(execution.results, key=lambda item: item.id)
        ],
    }


def serialize_result(result: BenchmarkResult):
    return {
        "id": result.id,
        "execution_id": result.execution_id,
        "dataset_query_id": result.dataset_query_id,
        "provider": result.provider,
        "query_text": result.query_text,
        "status": result.status,
        "latency_ms": result.latency_ms,
        "mentioned": bool(result.mentioned),
        "rank": result.rank,
        "recommendation_found": bool(result.recommendation_found),
        "citation_count": result.citation_count,
        "visibility_score": result.visibility_score,
        "response_length": result.response_length,
        "response_snippet": result.response_snippet,
        "raw_response": result.raw_response,
        "metrics": parse_json(result.metrics_json, {}),
        "error_message": result.error_message,
        "created_at": result.created_at,
    }


def parse_json(value: str | None, fallback):
    if not value:
        return fallback

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
