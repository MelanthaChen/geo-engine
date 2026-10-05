"""Freeze target-plus-reference source sets for training query contexts."""

from datetime import datetime, timezone
import hashlib
from urllib.parse import urlparse

from app.ge.search_provider import (
    provider_id,
    retrieval_result_ledger,
)
from app.ge.search_provider_factory import build_search_provider
from app.services.website_audit.crawler import fetch_page
from app.services.website_audit.extractor import extract_page
from app.teacher_pipeline.query_contexts import QUERY_POLICY_VERSION, resolve_audited_target


class TrainingContextBuildError(ValueError):
    pass


class TrainingContextBuilder:
    def __init__(self, search_provider=None):
        self.search_provider = search_provider or build_search_provider()

    def freeze(self, contexts: list, *, audit=None, on_progress=None) -> list[dict]:
        target_cache = {}
        entries = []
        for context in contexts:
            retrieved_at = datetime.now(timezone.utc)
            candidates = self.search_provider.search(query=context.query, top_k=10)
            retrieval_provider = provider_id(self.search_provider, candidates)
            target_page, target_rank, target_status = resolve_audited_target(
                audit, context.query, candidates
            )
            if target_page is None:
                if on_progress:
                    on_progress(len(entries), len(contexts), context.query)
                continue
            target = target_cache.get(target_page.url)
            if target is None:
                target = extract_page(fetch_page(target_page.url, timeout_seconds=20))
                if target.status_code != 200 or not target.body_text.strip():
                    raise TrainingContextBuildError(
                        f"Target page could not be snapshotted: {target_page.url}"
                    )
                target_cache[target_page.url] = target
            retrieved_at = next(
                (item.retrieved_at for item in candidates if item.retrieved_at),
                retrieved_at,
            )
            references = []
            seen = {target.url.rstrip("/")}
            target_host = self._host(target.url)
            for candidate in candidates:
                normalized = candidate.url.rstrip("/")
                if not candidate.plain_text.strip() or normalized in seen or self._host(candidate.url) == target_host:
                    continue
                seen.add(normalized)
                references.append(candidate)
                if len(references) == 4:
                    break
            if len(references) != 4:
                raise TrainingContextBuildError(
                    f"Query did not produce four distinct external references: {context.query}"
                )

            common = {
                "retrieval_provider": retrieval_provider,
                "retrieved_at": retrieved_at.isoformat(),
                "query_policy_version": QUERY_POLICY_VERSION,
                "source_audit_id": context.originating_evidence["audit_id"],
            }
            documents = [{
                "rank": 1,
                "title": target.page_title or target.h1 or context.target_url,
                "url": target.url,
                "content": target.body_text,
                "is_optimization_target": True,
                "source_role": "audited_target",
                "content_sha256": self._sha256(target.body_text),
                **common,
                "retrieval_provider": "injected_for_controlled_experiment",
            }]
            documents.extend({
                "rank": rank,
                "title": reference.title,
                "url": reference.url,
                "content": reference.plain_text,
                "is_optimization_target": False,
                "source_role": "reference",
                "content_sha256": reference.content_sha256 or self._sha256(reference.plain_text),
                **common,
            } for rank, reference in enumerate(references, start=2))

            supporting_evidence = {
                **context.originating_evidence,
                "query_source": context.query_source,
                "query_intent": context.query_intent,
                "source_mode": "generated_query",
                "training_eligible": True,
                "retrieval_query": context.query,
                "retrieval_results": retrieval_result_ledger(candidates),
                "target_retrieval_status": target_status,
                "target_page_id": target_page.id,
                "target_retrieval_rank": target_rank,
                "source_order": [document["url"] for document in documents],
                "source_snapshot_hashes": [
                    document["content_sha256"] for document in documents
                ],
                "target_index": 0,
            }
            for document in documents:
                document["supporting_evidence"] = supporting_evidence
            entries.append({"query": context.query, "documents": documents})
            if on_progress:
                on_progress(len(entries), len(contexts), context.query)
        return entries

    @staticmethod
    def _host(url: str) -> str:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
