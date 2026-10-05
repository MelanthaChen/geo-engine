"""Controlled Princeton-style validation for one audited website page."""

from datetime import datetime, timezone
import hashlib
from urllib.parse import urlparse

from sqlalchemy.orm import Session, joinedload

from app.core.url_identity import canonical_url_identity
from app.ge.search_provider import (
    provider_id,
    retrieval_result_ledger,
)
from app.ge.search_provider_factory import build_search_provider
from app.experiment.demo_reference_pack import (
    DEMO_AUDIT_EVIDENCE,
    DEMO_FROZEN_AT,
    DEMO_QUERY,
    DEMO_QUERY_POLICY_VERSION,
    DEMO_TARGET_SHA256,
    DEMO_TARGET_SNAPSHOT,
    DEMO_WORKFLOW,
    is_demo_property,
    load_demo_reference_documents,
)
from app.models.website_audit import WebsiteAudit
from app.services.website_audit.crawler import fetch_page
from app.services.website_audit.extractor import extract_page


QUERY_POLICY_VERSION = "audit-evidence-query-v1"


class NewWebsiteValidationError(ValueError):
    pass


class NewWebsiteValidationBuilder:
    """Freeze one audited target plus four external reference sources."""

    def __init__(self, db: Session, search_provider=None):
        self.db = db
        # Frozen validation must not require credentials for the live provider.
        # Resolve the configured provider only after the demo path has been
        # ruled out.
        self.search_provider = search_provider

    def build(self, *, property_id: int, audit_id: int, opportunity_id: int) -> dict:
        audit = (
            self.db.query(WebsiteAudit)
            .options(
                joinedload(WebsiteAudit.property),
                joinedload(WebsiteAudit.pages),
                joinedload(WebsiteAudit.recommendations),
            )
            .filter(
                WebsiteAudit.id == audit_id,
                WebsiteAudit.property_id == property_id,
                WebsiteAudit.status == "completed",
            )
            .first()
        )
        if audit is None:
            raise NewWebsiteValidationError(
                "The requested completed audit does not belong to this website."
            )
        recommendation = next(
            (item for item in audit.recommendations if item.id == opportunity_id),
            None,
        )
        if recommendation is None:
            raise NewWebsiteValidationError(
                "The requested optimization opportunity does not belong to this audit."
            )

        if is_demo_property(audit.property):
            return self._build_demo_pack(audit, recommendation)

        search_provider = self.search_provider or build_search_provider()

        query, evidence = self._query(audit, recommendation)
        retrieved_at = datetime.now(timezone.utc)
        candidates = search_provider.search(query=query, top_k=10)
        retrieval_provider = provider_id(search_provider, candidates)
        retrieved_at = next(
            (item.retrieved_at for item in candidates if item.retrieved_at),
            retrieved_at,
        )

        target_page, target_rank, target_status = self._select_target_page(
            audit, recommendation, candidates
        )
        if target_page is None:
            raise NewWebsiteValidationError(
                "The retrieval results did not identify an audited target page, "
                "and the audit opportunity has no valid evidence page to inject."
            )
        target_url = target_page.url
        target = extract_page(fetch_page(target_url, timeout_seconds=20))
        if target.status_code != 200 or not target.body_text.strip():
            raise NewWebsiteValidationError(
                f"Audited target page could not be snapshotted: {target_url} "
                f"(HTTP {target.status_code or 'unavailable'})."
            )

        evidence.update({
            "target_page_id": target_page.id,
            "target_page_url": target_page.url,
            "target_retrieval_rank": target_rank,
        })
        target_host = self._host(target.url)
        references = []
        seen_urls = {target.url.rstrip("/")}
        for candidate in candidates:
            normalized_url = candidate.url.rstrip("/")
            if (
                not candidate.plain_text.strip()
                or normalized_url in seen_urls
                or self._host(candidate.url) == target_host
            ):
                continue
            seen_urls.add(normalized_url)
            references.append(candidate)
            if len(references) == 4:
                break
        if len(references) != 4:
            raise NewWebsiteValidationError(
                "The configured retrieval provider did not return four distinct "
                "external reference sources for the frozen experiment set."
            )

        common = {
            "retrieval_provider": retrieval_provider,
            "retrieved_at": retrieved_at.isoformat(),
            "query_policy_version": QUERY_POLICY_VERSION,
            "source_audit_id": audit.id,
        }
        documents = [{
            "rank": 1,
            "title": target.page_title or target.h1 or audit.property.name,
            "url": target.url,
            "content": target.body_text,
            "is_optimization_target": True,
            "source_role": "audited_target",
            "content_sha256": self._sha256(target.body_text),
            **common,
            "retrieval_provider": "injected_for_controlled_experiment",
        }]
        documents.extend({
            "rank": index,
            "title": document.title,
            "url": document.url,
            "content": document.plain_text,
            "is_optimization_target": False,
            "source_role": "reference",
            "content_sha256": self._sha256(document.plain_text),
            **common,
        } for index, document in enumerate(references, start=2))

        supporting_evidence = {
            **evidence,
            "retrieval_query": query,
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

        return {
            "query": query,
            "documents": documents,
            "metadata": {
                **common,
                "workflow": "princeton-style-new-website-validation-v1",
                "target_index": 0,
                "target_rank": 1,
                "target_url": target.url,
                "source_order": [document["url"] for document in documents],
                "source_snapshot_hashes": [
                    document["content_sha256"] for document in documents
                ],
                "retrieval_query": query,
                "retrieval_results": retrieval_result_ledger(candidates),
                "target_retrieval_status": target_status,
                "target_page_id": target_page.id,
                "target_retrieval_rank": target_rank,
            },
        }

    def _build_demo_pack(self, audit, recommendation) -> dict:
        target_url = audit.base_url
        target = extract_page(fetch_page(target_url, timeout_seconds=20))
        if target.status_code != 200 or not target.body_text.strip():
            raise NewWebsiteValidationError(
                f"Frozen GeoAIResume target could not be snapshotted: {target_url}"
            )
        target_hash = self._sha256(target.body_text)
        if target_hash != DEMO_TARGET_SHA256:
            raise NewWebsiteValidationError(
                "Frozen GeoAIResume target content failed its integrity check."
            )
        references = load_demo_reference_documents()
        evidence = {
            **DEMO_AUDIT_EVIDENCE,
            "audit_id": audit.id,
            "recommendation_id": recommendation.id,
            "audit_brand_summary": audit.brand_summary,
            "audit_product_summary": audit.product_summary,
        }
        common = {
            "retrieval_provider": "frozen-geo-bench-cache",
            "retrieved_at": DEMO_FROZEN_AT.isoformat(),
            "query_policy_version": DEMO_QUERY_POLICY_VERSION,
            "source_audit_id": audit.id,
            "supporting_evidence": evidence,
        }
        documents = [{
            "rank": 1,
            "title": target.page_title or target.h1 or "GeoAIResume",
            "url": target.url,
            "content": target.body_text,
            "is_optimization_target": True,
            "source_role": "audited_target",
            "content_sha256": target_hash,
            **common,
            "retrieval_provider": "frozen-production-page-snapshot",
            "retrieved_at": DEMO_TARGET_SNAPSHOT["captured_at"],
        }]
        documents.extend({
            **reference,
            "is_optimization_target": False,
            "source_role": "reference",
            **common,
        } for reference in references)
        return {
            "query": DEMO_QUERY,
            "documents": documents,
            "metadata": {
                **common,
                "workflow": DEMO_WORKFLOW,
                "target_index": 0,
                "target_rank": 1,
                "target_url": target.url,
                "source_order": [document["url"] for document in documents],
            },
        }

    @staticmethod
    def _select_target_page(audit, recommendation, candidates):
        eligible_pages = {
            canonical_url_identity(page.url): page
            for page in audit.pages
            if page.status_code == 200
            and not page.is_duplicate
            and page.word_count > 0
            and canonical_url_identity(page.url)
        }
        matches = [
            (candidate.rank, eligible_pages[canonical_url_identity(candidate.url)])
            for candidate in candidates
            if canonical_url_identity(candidate.url) in eligible_pages
        ]
        if matches:
            rank, page = min(matches, key=lambda item: item[0])
            return page, rank, "retrieved_by_provider"

        evidence_identity = canonical_url_identity(recommendation.evidence_url or "")
        page = eligible_pages.get(evidence_identity)
        if page is not None:
            return page, None, "injected_for_controlled_experiment"
        return None, None, None

    @staticmethod
    def _query(audit, recommendation) -> tuple[str, dict]:
        brand = (audit.property.brand_name or audit.property.name).strip()
        topic = (
            audit.product_summary
            or recommendation.title
            or brand
        ).strip().rstrip(".?!")
        query = f"What should someone know about {topic} from {brand}?"
        evidence = {
            "audit_id": audit.id,
            "recommendation_id": recommendation.id,
            "recommendation_category": recommendation.category,
            "recommendation_title": recommendation.title,
            "recommendation_description": recommendation.description,
            "recommendation_evidence_url": recommendation.evidence_url,
            "brand": brand,
        }
        return query, evidence

    @staticmethod
    def _host(url: str) -> str:
        return urlparse(url).netloc.lower().removeprefix("www.")

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
