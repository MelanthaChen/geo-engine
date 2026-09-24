"""Canonical provenance assembly and hashing."""

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def provenance_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def build_provenance(*, experiment, query, baseline_run, optimized_run, audit, selected_document, aggregate_metrics) -> dict[str, Any]:
    return {
        "schema_version": "teacher-provenance-v1",
        "website_id": experiment.property_id,
        "audit": {
            "id": audit.id,
            "version": "website-audit-schema-v1",
            "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
            "base_url": audit.base_url,
        },
        "experiment": {
            "id": experiment.id,
            "dataset_name": experiment.dataset_name,
            "dataset_version": experiment.dataset_version,
            "random_seed": experiment.random_seed,
            "temperature": experiment.temperature,
            "completed_at": experiment.completed_at.isoformat() if experiment.completed_at else None,
        },
        "query": {
            "id": query.id,
            "text": query.query,
            "seed_value": query.seed_value,
            "selected_document_rank": query.selected_document_rank,
            "query_policy_version": query.query_policy_version,
            "source_audit_id": query.source_audit_id,
            "supporting_audit_evidence": json.loads(query.supporting_evidence_json or "{}"),
            "retrieval_provider": query.retrieval_provider,
            "retrieval_timestamp": query.retrieval_timestamp.isoformat() if query.retrieval_timestamp else None,
        },
        "selected_document": {
            "url": selected_document.url,
            "title": selected_document.title,
            "rank": selected_document.rank,
            "content_sha256": hashlib.sha256(selected_document.plain_text.encode("utf-8")).hexdigest(),
            "source_role": selected_document.source_role,
        },
        "source_set": [
            {
                "rank": document.rank,
                "url": document.url,
                "title": document.title,
                "source_role": document.source_role,
                "is_target": document.is_selected,
                "retrieval_provider": document.retrieval_provider,
                "retrieval_timestamp": document.retrieval_timestamp.isoformat() if document.retrieval_timestamp else None,
                "content_sha256": document.content_sha256 or hashlib.sha256(document.plain_text.encode("utf-8")).hexdigest(),
                "snapshot_text": document.plain_text,
            }
            for document in sorted(query.documents, key=lambda item: item.rank)
        ],
        "aggregate_metrics": aggregate_metrics,
        "baseline_run": run_provenance(baseline_run),
        "optimized_run": run_provenance(optimized_run),
    }


def run_provenance(run) -> dict[str, Any]:
    return {
        "id": run.id,
        "strategy": run.strategy,
        "sample_index": run.sample_index,
        "seed_value": run.seed_value,
        "provider": run.provider,
        "model": run.model,
        "prompt_version_id": run.prompt_version_id,
        "prompt_version": run.prompt_version.version if run.prompt_version else None,
        "generation_parameters": json.loads(run.generation_params_json or "{}"),
        "raw_prompt_sha256": hashlib.sha256(run.raw_prompt.encode("utf-8")).hexdigest(),
        "raw_response_sha256": hashlib.sha256((run.raw_response or "").encode("utf-8")).hexdigest(),
        "evaluation_versions": sorted(
            f"{evaluation.evaluator}:{evaluation.evaluator_version}"
            for evaluation in run.evaluations
        ),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
