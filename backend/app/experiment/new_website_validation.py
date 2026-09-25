"""Controlled Princeton-style validation for one audited website page."""

from datetime import datetime, timezone
import hashlib
from urllib.parse import urlparse

from sqlalchemy.orm import Session, joinedload

from app.ge.google_search_provider import GoogleSearchProvider
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
from app.models.website_audit_recommendation import WebsiteAuditRecommendation
from app.services.website_audit.crawler import fetch_page
from app.services.website_audit.extractor import extract_page


QUERY_POLICY_VERSION = "audit-evidence-query-v1"
RETRIEVAL_PROVIDER = "google-custom-search-api"


class NewWebsiteValidationError(ValueError):
    pass


class NewWebsiteValidationBuilder:
    """Freeze one audited target plus four external reference sources."""

    def __init__(self, db: Session, search_provider=None):
        self.db = db
        self.search_provider = search_provider or GoogleSearchProvider(
            require_api_credentials=True
        )

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

        target_url = self._target_url(audit, recommendation)
        target = extract_page(fetch_page(target_url, timeout_seconds=20))
        if target.status_code != 200 or not target.body_text.strip():
            raise NewWebsiteValidationError(
                f"Audited target page could not be snapshotted: {target_url} "
                f"(HTTP {target.status_code or 'unavailable'})."
            )

        query, evidence = self._query(audit, recommendation, target)
        retrieved_at = datetime.now(timezone.utc)
        candidates = self.search_provider.search(query=query, top_k=10)
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
            "retrieval_provider": RETRIEVAL_PROVIDER,
            "retrieved_at": retrieved_at.isoformat(),
            "query_policy_version": QUERY_POLICY_VERSION,
            "source_audit_id": audit.id,
            "supporting_evidence": evidence,
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
    def _target_url(audit, recommendation: WebsiteAuditRecommendation) -> str:
        successful_urls = {
            page.url for page in audit.pages if page.status_code == 200
        }
        if recommendation.evidence_url in successful_urls:
            return recommendation.evidence_url
        if audit.base_url in successful_urls:
            return audit.base_url
        if successful_urls:
            return sorted(successful_urls)[0]
        return audit.base_url

    @staticmethod
    def _query(audit, recommendation, target) -> tuple[str, dict]:
        brand = (audit.property.brand_name or audit.property.name).strip()
        topic = (
            target.h1
            or target.page_title
            or audit.product_summary
            or recommendation.title
        ).strip().rstrip(".?!")
        query = f"What should someone know about {topic} from {brand}?"
        evidence = {
            "audit_id": audit.id,
            "recommendation_id": recommendation.id,
            "recommendation_category": recommendation.category,
            "recommendation_title": recommendation.title,
            "recommendation_description": recommendation.description,
            "recommendation_evidence_url": recommendation.evidence_url,
            "target_page_title": target.page_title,
            "target_page_h1": target.h1,
            "brand": brand,
        }
        return query, evidence

    @staticmethod
    def _host(url: str) -> str:
        return urlparse(url).netloc.lower().removeprefix("www.")

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
