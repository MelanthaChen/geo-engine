"""Canonical provenance assembly and hashing."""

import hashlib
import json
from typing import Any

from app.core.url_identity import canonical_url_identity


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def provenance_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def context_fingerprint(*, query, strategy: str) -> str:
    payload = {
        "query": " ".join(query.query.lower().split()),
        "strategy": strategy,
        "source_set": [
            {
                "rank": document.rank,
                "url": document.url.rstrip("/"),
                "content_sha256": document.content_sha256
                or hashlib.sha256(document.plain_text.encode("utf-8")).hexdigest(),
                "is_target": document.is_selected,
            }
            for document in sorted(query.documents, key=lambda item: item.rank)
        ],
    }
    return provenance_hash(payload)


def build_provenance(*, experiment, query, baseline_run, optimized_run, audit, selected_document, aggregate_metrics) -> dict[str, Any]:
    supporting_evidence = json.loads(query.supporting_evidence_json or "{}")
    frozen_demo = any(
        "frozen" in (document.retrieval_provider or "")
        for document in query.documents
    )
    source_mode = supporting_evidence.get("source_mode") or (
        "frozen_demo" if frozen_demo else
        "benchmark" if experiment.dataset_name == "geo_bench" else
        "generated_query" if experiment.dataset_name == "teacher_training_contexts" else
        "live_retrieval"
    )
    training_eligible = bool(
        supporting_evidence.get("training_eligible", source_mode != "frozen_demo")
    )
    target_page_id = _target_page_id(audit, selected_document.url, supporting_evidence)
    optimized_parameters = json.loads(optimized_run.generation_params_json or "{}")
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
            "supporting_audit_evidence": supporting_evidence,
            "query_source": supporting_evidence.get("query_source") or (
                "benchmark" if source_mode == "benchmark" else "generated"
            ),
            "query_intent": supporting_evidence.get("query_intent"),
            "originating_page_id": target_page_id,
            "originating_page_url": supporting_evidence.get("page_url") or selected_document.url,
            "retrieval_provider": query.retrieval_provider,
            "retrieval_timestamp": query.retrieval_timestamp.isoformat() if query.retrieval_timestamp else None,
            "retrieval_query": supporting_evidence.get("retrieval_query") or query.query,
            "retrieval_results": supporting_evidence.get("retrieval_results", []),
            "target_retrieval_status": supporting_evidence.get(
                "target_retrieval_status"
            ),
        },
        "selected_document": {
            "page_id": target_page_id,
            "url": selected_document.url,
            "title": selected_document.title,
            "rank": selected_document.rank,
            "content_sha256": hashlib.sha256(selected_document.plain_text.encode("utf-8")).hexdigest(),
            "source_role": selected_document.source_role,
        },
        "context_fingerprint": context_fingerprint(
            query=query,
            strategy=optimized_run.strategy,
        ),
        "source_mode": source_mode,
        "training_eligible": training_eligible,
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
        "baseline_answer": baseline_run.raw_response,
        "treatment_answer": optimized_run.raw_response,
        "original_target_content": selected_document.plain_text,
        "rewrite_plan": optimized_parameters.get("rewrite_plan"),
        "optimized_target_content": (
            optimized_run.strategy_result.modified_document_text
            if optimized_run.strategy_result else None
        ),
    }


def _target_page_id(audit, target_url: str, supporting_evidence: dict[str, Any]) -> int | None:
    recorded = supporting_evidence.get("page_id") or supporting_evidence.get("target_page_id")
    if recorded is not None:
        return recorded
    target_identity = canonical_url_identity(target_url)
    for page in getattr(audit, "pages", []) or []:
        if canonical_url_identity(page.url) == target_identity:
            return page.id
    return None


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
