"""Objective, presentation-ready features derived from stored audit evidence."""

from typing import Any

from app.models.website_audit import WebsiteAudit


UNAVAILABLE_FEATURES = (
    (
        "statistics_density",
        "Statistics Density",
        "Quantitative-fact extraction is not available in the current audit.",
    ),
    (
        "citation_density",
        "Citation Density",
        "The current audit counts external links, but does not classify citations.",
    ),
    (
        "readability",
        "Readability",
        "No readability analyzer is implemented in the current audit.",
    ),
    (
        "technical_terminology",
        "Technical Terminology",
        "No terminology classifier is implemented in the current audit.",
    ),
    (
        "schema_presence",
        "Schema Presence",
        "Structured-data markup is not extracted by the current audit.",
    ),
    (
        "freshness",
        "Freshness",
        "Publication and modification dates are not extracted by the current audit.",
    ),
)


def build_website_profile(audit: WebsiteAudit) -> dict[str, Any]:
    pages = evidence_pages(audit)
    successful_pages = [page for page in pages if page.status_code == 200]
    page_count = len(pages)
    successful_count = len(successful_pages)
    total_words = sum(page.word_count or 0 for page in successful_pages)
    internal_references = sum(
        page.internal_link_count or 0 for page in successful_pages
    )
    external_references = sum(
        page.external_link_count or 0 for page in successful_pages
    )
    pages_with_h1 = sum(bool(page.h1) for page in successful_pages)
    pages_with_meta = sum(bool(page.meta_description) for page in successful_pages)

    return {
        "website_health_score": audit.overall_geo_score,
        "content_quality_score": audit.content_coverage_score,
        "technical_quality_score": audit.website_structure_score,
        "authority_score": audit.trust_signals_score,
        "readability_score": None,
        "pages_crawled": audit.requested_url_count or len(audit.pages),
        "successful_pages": successful_count,
        "total_word_count": total_words,
        "internal_references": internal_references,
        "external_references": external_references,
        "measurement_notes": {
            "website_health_score": "Existing overall audit score.",
            "content_quality_score": "Existing content coverage score.",
            "technical_quality_score": "Existing website structure score.",
            "authority_score": "Existing trust signals score.",
            "readability_score": "Unavailable; no readability analyzer is implemented.",
        },
        "_evidence": {
            "pages_with_h1": pages_with_h1,
            "pages_with_meta": pages_with_meta,
        },
    }


def build_findings(audit: WebsiteAudit) -> tuple[list[dict], list[dict]]:
    profile = build_website_profile(audit)
    pages = evidence_pages(audit)
    successful = profile["successful_pages"]
    strengths: list[dict] = []
    weaknesses: list[dict] = []

    if successful:
        strengths.append(
            finding(
                "Pages were successfully retrieved",
                f"{successful} of {len(pages)} crawled pages returned HTTP 200.",
                "http_status",
            )
        )

    h1_count = profile["_evidence"]["pages_with_h1"]
    meta_count = profile["_evidence"]["pages_with_meta"]
    if successful and h1_count == successful:
        strengths.append(
            finding(
                "H1 coverage is complete",
                f"All {successful} successfully retrieved pages contain an H1.",
                "heading_structure",
            )
        )
    elif successful and h1_count < successful:
        weaknesses.append(
            finding(
                "Some pages have no detected H1",
                f"{successful - h1_count} of {successful} successfully retrieved pages have no detected H1.",
                "heading_structure",
            )
        )

    if successful and meta_count == successful:
        strengths.append(
            finding(
                "Meta description coverage is complete",
                f"All {successful} successfully retrieved pages contain a meta description.",
                "metadata_coverage",
            )
        )
    elif successful and meta_count < successful:
        weaknesses.append(
            finding(
                "Some pages have no detected meta description",
                f"{successful - meta_count} of {successful} successfully retrieved pages have no detected meta description.",
                "metadata_coverage",
            )
        )

    failed = len(pages) - successful
    if failed:
        weaknesses.append(
            finding(
                "Some crawled pages were not successfully retrieved",
                f"{failed} of {len(pages)} crawled pages did not return HTTP 200.",
                "http_status",
            )
        )

    if successful and profile["external_references"] == 0:
        weaknesses.append(
            finding(
                "No external references were detected",
                f"Zero external links were found across {successful} successfully retrieved pages.",
                "external_references",
            )
        )
    elif profile["external_references"]:
        strengths.append(
            finding(
                "External references are present",
                f"{profile['external_references']} external links were detected across the crawled pages.",
                "external_references",
            )
        )

    if successful and profile["internal_references"] == 0:
        weaknesses.append(
            finding(
                "No internal references were detected",
                f"Zero internal links were found across {successful} successfully retrieved pages.",
                "internal_references",
            )
        )

    if not pages:
        weaknesses.append(
            finding(
                "No page evidence is available",
                "The audit did not retain any crawled pages.",
                "crawl_coverage",
            )
        )

    return strengths, weaknesses


def build_website_features(audit: WebsiteAudit) -> dict[str, dict[str, Any]]:
    profile = build_website_profile(audit)
    successful = profile["successful_pages"]
    h1_count = profile["_evidence"]["pages_with_h1"]

    features: dict[str, dict[str, Any]] = {
        "authority_score": feature(
            "Authority Signals", audit.trust_signals_score, "score", score_availability(audit.trust_signals_score),
            "Existing trust signals score from the current audit.",
        ),
        "faq_presence": feature(
            "FAQ Coverage", audit.faq_coverage_score, "score", score_availability(audit.faq_coverage_score),
            "Existing FAQ coverage score based on detected paths and text.",
        ),
        "heading_structure": feature(
            "Heading Structure", h1_count, "pages with H1", "available",
            f"{h1_count} of {successful} successfully retrieved pages contain an H1.",
        ),
        "external_references": feature(
            "External References", profile["external_references"], "links", "available",
            "Sum of detected external links across successfully retrieved pages.",
        ),
        "internal_references": feature(
            "Internal References", profile["internal_references"], "links", "available",
            "Sum of detected internal links across successfully retrieved pages.",
        ),
        "word_count": feature(
            "Word Count", profile["total_word_count"], "words", "available",
            "Sum of extracted words across successfully retrieved pages.",
        ),
        "content_coverage": feature(
            "Content Coverage", audit.content_coverage_score, "score", score_availability(audit.content_coverage_score),
            "Existing content coverage score from the current audit.",
        ),
        "website_structure": feature(
            "Website Structure", audit.website_structure_score, "score", score_availability(audit.website_structure_score),
            "Existing website structure score from detected site paths.",
        ),
        "brand_clarity": feature(
            "Brand Clarity", audit.brand_clarity_score, "score", score_availability(audit.brand_clarity_score),
            "Existing brand clarity score based on H1 and meta-description presence.",
        ),
    }
    for key, label, evidence in UNAVAILABLE_FEATURES:
        features[key] = feature(label, None, None, "unavailable", evidence)
    return features


def build_optimization_opportunities(audit: WebsiteAudit) -> list[dict[str, Any]]:
    opportunities = []
    for recommendation in audit.recommendations:
        opportunities.append(
            {
                "id": recommendation.id,
                "category": recommendation.category,
                "title": neutral_title(recommendation.category, recommendation.title),
                "direction": neutral_direction(recommendation.category),
                "priority": recommendation.priority,
                "evidence": opportunity_evidence(recommendation),
                "evidence_url": recommendation.evidence_url,
                "basis": "objective_audit_finding",
                "validation_status": "not_validated",
                "predicted_gain": None,
            }
        )
    return opportunities


def feature(label, value, unit, availability, evidence):
    return {
        "label": label,
        "value": value,
        "unit": unit,
        "availability": availability,
        "evidence": evidence,
    }


def evidence_pages(audit: WebsiteAudit) -> list:
    has_extraction_counts = audit.extraction_success_count is not None
    return [
        page for page in audit.pages
        if not getattr(page, "is_duplicate", False)
        and (not has_extraction_counts or bool(page.content_sha256))
    ]


def score_availability(value) -> str:
    return "available" if value is not None else "unavailable"


def finding(label: str, evidence: str, feature_key: str) -> dict[str, str]:
    return {"label": label, "evidence": evidence, "feature_key": feature_key}


def neutral_title(category: str, fallback: str) -> str:
    cleaned = fallback
    for prefix in ("Create a ", "Create an ", "Add ", "Strengthen "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    labels = {
        "missing_pages": "Page coverage",
        "missing_geo_topics": "Topic coverage",
        "internal_linking_suggestions": "Internal references",
        "faq_opportunities": "FAQ coverage",
        "content_recommendations": "Content coverage",
    }
    label = labels.get(category, "Observed area")
    return f"{label}: {cleaned.rstrip('.')}"


def neutral_direction(category: str) -> str:
    directions = {
        "missing_pages": "Review whether a dedicated page is appropriate for the detected coverage gap.",
        "missing_geo_topics": "Review whether the absent topic belongs in the website's content scope.",
        "internal_linking_suggestions": "Review the internal links associated with the observed page evidence.",
        "faq_opportunities": "Review whether the detected question gap should be represented as FAQ content.",
        "content_recommendations": "Review whether additional content is appropriate for the detected coverage gap.",
    }
    return directions.get(category, "Review this observed area as a possible optimization direction.")


def opportunity_evidence(recommendation) -> str:
    evidence = recommendation.description
    if recommendation.evidence_url:
        evidence = f"{evidence} Observed page: {recommendation.evidence_url}."
    return evidence
