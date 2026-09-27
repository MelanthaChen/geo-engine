"""Objective, presentation-ready features derived from stored audit evidence."""

from typing import Any

from app.models.website_audit import WebsiteAudit
from app.services.website_audit.evidence import aggregate_site_evidence, page_evidence


def build_website_profile(audit: WebsiteAudit) -> dict[str, Any]:
    pages = evidence_pages(audit)
    successful_pages = [
        page for page in pages
        if page.status_code is not None and 200 <= page.status_code < 300
    ]
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

    requested = audit.requested_url_count or len(audit.pages)
    successful_responses = (
        audit.successful_response_count
        if audit.successful_response_count is not None
        else sum(
            page.status_code is not None and 200 <= page.status_code < 300
            for page in audit.pages
        )
    )
    if requested and successful_responses:
        strengths.append(
            finding(
                "Pages were successfully retrieved",
                f"{successful_responses} of {requested} requested URLs returned successful HTTP responses.",
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

    unsuccessful_html = max(
        requested - audit.accepted_html_response_count,
        0,
    ) if audit.accepted_html_response_count is not None else 0
    if unsuccessful_html:
        weaknesses.append(
            finding(
                "Some requested URLs did not return successful HTML",
                f"{unsuccessful_html} of {requested} requested URLs did not return a successful accepted HTML response.",
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
                f"{profile['external_references']} external links were detected across {successful} analyzed pages.",
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
    pages = evidence_pages(audit)
    strategy_summary = aggregate_site_evidence(pages)
    evidence_documents = [page_evidence(page) for page in pages if page_evidence(page)]
    sentence_lengths = [
        document.get("strategies", {}).get("easy_to_understand", {}).get("average_sentence_words")
        for document in evidence_documents
    ]
    sentence_lengths = [value for value in sentence_lengths if isinstance(value, (int, float))]
    prominent_terms = list(dict.fromkeys(
        term
        for document in evidence_documents
        for term in document.get("strategies", {}).get("technical_terms", {}).get("prominent_terms", [])
    ))[:12]
    schema_types = list(strategy_summary["structured_data"])
    strategy_evidence_available = strategy_summary["analyzed_pages"] > 0

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
        "statistics_density": feature(
            "Quantitative Statements",
            strategy_summary["statistics"]["quantitative_statements"],
            "detected statements",
            "available" if strategy_evidence_available else "unavailable",
            "Count of deterministic numeric evidence detections; values are not fact-checked.",
        ),
        "citation_density": feature(
            "Reference-like Links",
            strategy_summary["citations"]["reference_like_links"],
            "links",
            "available" if strategy_evidence_available else "unavailable",
            "Outbound links with source, study, report, paper, or equivalent attribution evidence.",
        ),
        "readability": feature(
            "Average Sentence Length",
            round(sum(sentence_lengths) / len(sentence_lengths), 1) if sentence_lengths else None,
            "words",
            "available" if sentence_lengths else "unavailable",
            "Structural sentence-length evidence only; no reading-grade or fluency score is inferred.",
        ),
        "technical_terminology": feature(
            "Prominent Extracted Terms",
            ", ".join(prominent_terms) if prominent_terms else None,
            None,
            "available" if prominent_terms else "unavailable",
            "Deterministic prominent terms from headings and normalized token frequency.",
        ),
        "schema_presence": feature(
            "Structured Data Types",
            ", ".join(schema_types) if schema_types else None,
            None,
            "available" if schema_types else "unavailable",
            "JSON-LD schema types observed in admitted representative-page evidence.",
        ),
        "freshness": feature(
            "Pages with Publication or Update Dates",
            strategy_summary["authorship"]["pages_with_dates"],
            "pages",
            "available" if strategy_evidence_available else "unavailable",
            "Count of pages exposing deterministic publication or modification date metadata.",
        ),
    }
    return features


def build_optimization_opportunities(audit: WebsiteAudit) -> list[dict[str, Any]]:
    opportunities = []
    for recommendation in audit.recommendations:
        if (
            recommendation.observed_evidence is None
            or recommendation.affected_page_count is None
            or recommendation.evaluated_page_count is None
            or recommendation.why_it_matters is None
        ):
            continue
        opportunities.append(
            {
                "id": recommendation.id,
                "category": recommendation.category,
                "title": neutral_title(recommendation.category, recommendation.title),
                "direction": neutral_direction(recommendation.category),
                "priority": recommendation.priority,
                "evidence": opportunity_evidence(recommendation),
                "observed_evidence": recommendation.observed_evidence,
                "affected_page_count": recommendation.affected_page_count,
                "evaluated_page_count": recommendation.evaluated_page_count,
                "why_it_matters": recommendation.why_it_matters,
                "evidence_url": recommendation.evidence_url,
                "affected_urls": (
                    recommendation.evidence_json or {}
                ).get("affected_urls", []),
                "suggested_strategy": (
                    recommendation.evidence_json or {}
                ).get("suggested_strategy"),
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
    return fallback.rstrip(".")


def neutral_direction(category: str) -> str:
    directions = {
        "heading_structure": "Review the affected pages and add a descriptive H1 where appropriate.",
        "metadata_coverage": "Review the affected pages and add the missing document metadata where appropriate.",
        "http_html_success": "Investigate the affected URLs and their HTTP or content-type behavior.",
        "internal_linking_suggestions": "Review the internal links associated with the observed page evidence.",
        "faq_opportunities": "Review the affected explanatory pages for grounded FAQ / Q&A restructuring.",
        "statistics": "Review the affected explanatory pages for appropriate, verified quantitative evidence.",
        "citation": "Review the affected informational pages for relevant source attribution.",
        "authoritative": "Review explicit authorship, dates, and source provenance on the affected pages.",
    }
    return directions.get(category, "Review this observed area as a possible optimization direction.")


def opportunity_evidence(recommendation) -> str:
    evidence = recommendation.description
    if recommendation.evidence_url:
        evidence = f"{evidence} Observed page: {recommendation.evidence_url}."
    return evidence
