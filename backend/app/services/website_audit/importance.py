"""Deterministic, local GEO/content importance ranking for Website Audit."""

from collections import Counter
from dataclasses import dataclass
import re
from urllib.parse import urlparse

from app.services.website_audit.crawler import normalize_url, path_family, path_segments
from app.services.website_audit.extractor import PageExtract


COMPARISON_LANGUAGE = re.compile(
    r"\b(?:compare|comparison|compared|versus|vs\.?|difference|alternative)\b",
    re.IGNORECASE,
)
UTILITY_SEGMENTS = {
    "account", "auth", "cart", "checkout", "cookie", "cookies", "filter",
    "login", "logout", "search", "signin", "signup", "tag",
}
LEGAL_SEGMENTS = {"legal", "privacy", "terms", "cookie", "cookies"}
PAGINATION_PATH = re.compile(r"/(?:page|p)/\d+(?:/|$)", re.IGNORECASE)


@dataclass(frozen=True)
class RankedPage:
    page: PageExtract
    score: int
    family: str
    reasons: tuple[str, ...]
    signals: dict


def select_geo_important_pages(
    pages: list[PageExtract],
    *,
    audited_url: str,
    homepage_url: str,
    homepage_links: set[str],
    sitemap_urls: set[str],
    limit: int,
) -> list[PageExtract]:
    """Stage B: rank extracted candidates, then select with family diversity."""
    if limit < 1:
        return []

    inbound_counts = internal_inbound_counts(pages)
    ranked = [
        rank_page(
            page,
            audited_url=audited_url,
            homepage_url=homepage_url,
            homepage_links=homepage_links,
            sitemap_urls=sitemap_urls,
            inbound_count=inbound_counts.get(normalize_url(page.url), 0),
        )
        for page in pages
        if is_analyzable_unique_page(page)
    ]
    ranked.sort(key=lambda item: (-item.score, item.page.url))

    selected: list[RankedPage] = []
    audited = next((item for item in ranked if page_matches_url(item.page, audited_url)), None)
    if audited:
        selected.append(audited)

    by_family: dict[str, list[RankedPage]] = {}
    for item in ranked:
        if item is audited:
            continue
        by_family.setdefault(item.family, []).append(item)

    family_order = sorted(
        by_family,
        key=lambda family: (-by_family[family][0].score, family),
    )
    family_counts = Counter(item.family for item in selected)
    while len(selected) < limit:
        active_families = [family for family in family_order if by_family[family]]
        if not active_families:
            break
        minimum_selected = min(family_counts[family] for family in active_families)
        added = False
        for family in active_families:
            if family_counts[family] == minimum_selected and len(selected) < limit:
                selected.append(by_family[family].pop(0))
                family_counts[family] += 1
                added = True
        if not added:
            break

    for rank, item in enumerate(selected, start=1):
        page = item.page
        page.content_family = item.family
        page.selection_reasons = (*item.reasons, f"Representative of {item.family} content family")
        page.geo_importance_rank = rank
        page.geo_importance_score = item.score
        page.geo_importance_signals = item.signals
    return [item.page for item in selected]


def rank_page(
    page: PageExtract,
    *,
    audited_url: str,
    homepage_url: str,
    homepage_links: set[str],
    sitemap_urls: set[str],
    inbound_count: int,
) -> RankedPage:
    evidence = page.evidence or {}
    content = evidence.get("content", {})
    strategies = evidence.get("strategies", {})
    faq = strategies.get("faq", {})
    statistics = strategies.get("statistics", {})
    citation = strategies.get("citation", {})
    authority = strategies.get("authoritative", {})
    technical = strategies.get("technical_terms", {})
    structured = evidence.get("structured_data", {})
    authorship = evidence.get("authorship", {})
    family = path_family(page.url)
    segments = {segment.lower() for segment in path_segments(page.url)}

    is_audited = page_matches_url(page, audited_url)
    is_homepage = page_matches_url(page, homepage_url)
    from_homepage = any(page_matches_url(page, url) for url in homepage_links)
    in_sitemap = any(page_matches_url(page, url) for url in sitemap_urls)
    word_points = richness_word_points(page.word_count)
    heading_count = page.h2_count + page.h3_count + bool(page.h1)
    paragraph_count = int(content.get("paragraph_count") or 0)
    list_count = int(content.get("list_count") or 0)
    reference_count = int(citation.get("reference_like_link_count") or 0)
    numeric_count = int(statistics.get("numeric_claim_count") or 0)
    qa_count = int(faq.get("detected_qa_pair_count") or 0)
    methodology_count = int(authority.get("methodology_language_count") or 0)
    glossary_count = int(technical.get("glossary_definition_count") or 0)
    schema_count = len(structured.get("schema_types") or [])
    has_authorship = bool(authorship.get("author_name"))
    has_date = bool(authorship.get("published_date") or authorship.get("modified_date"))
    explanatory = bool(faq.get("explanatory_text_present"))
    comparison = bool(COMPARISON_LANGUAGE.search(page.body_text))
    canonical_valid = valid_same_site_canonical(page)
    utility = bool(segments & UTILITY_SEGMENTS)
    legal_only = bool(segments & LEGAL_SEGMENTS) and page.word_count < 800
    pagination = bool(PAGINATION_PATH.search(urlparse(page.url).path))

    components = {
        "audited_url": 100 if is_audited else 0,
        "homepage": 80 if is_homepage else 0,
        "homepage_link": 35 if from_homepage else 0,
        "internal_inbound_links": min(inbound_count * 4, 24),
        "shallow_depth": max(12 - len(path_segments(page.url)) * 3, 0),
        "sitemap_presence": 6 if in_sitemap else 0,
        "substantive_words": word_points,
        "heading_structure": min(heading_count * 2, 12),
        "paragraph_structure": min(paragraph_count, 8),
        "list_structure": min(list_count * 2, 6),
        "explanatory_content": 8 if explanatory else 0,
        "definitions": min(glossary_count * 3, 9),
        "quantitative_evidence": min(numeric_count, 10),
        "reference_links": min(reference_count * 5, 15),
        "authorship": 6 if has_authorship else 0,
        "publication_date": 3 if has_date else 0,
        "structured_data": min(schema_count * 2, 8),
        "question_answer_content": min(qa_count * 3, 12),
        "methodology_evidence": min(methodology_count * 2, 10),
        "comparison_content": 6 if comparison else 0,
        "canonical_quality": 5 if canonical_valid else 0,
        "usable_extraction": 5 if page.extraction_method in {"http", "browser"} else 0,
        "unique_content": 8 if not page.is_duplicate else 0,
        "thin_content_penalty": -35 if page.word_count < 40 else (-15 if page.word_count < 100 else 0),
        "utility_page_penalty": -40 if utility else 0,
        "pagination_penalty": -25 if pagination else 0,
        "legal_only_penalty": -25 if legal_only else 0,
    }
    score = sum(components.values())
    reasons = selection_reasons(
        is_audited=is_audited,
        is_homepage=is_homepage,
        from_homepage=from_homepage,
        inbound_count=inbound_count,
        word_count=page.word_count,
        explanatory=explanatory,
        numeric_count=numeric_count,
        reference_count=reference_count,
        has_authorship=has_authorship,
        schema_count=schema_count,
        qa_count=qa_count,
        methodology_count=methodology_count,
        comparison=comparison,
    )
    signals = {
        "version": "geo-page-importance-v1",
        "score_components": components,
        "internal_inbound_link_count": inbound_count,
        "word_count": page.word_count,
        "heading_count": heading_count,
        "paragraph_count": paragraph_count,
        "list_count": list_count,
        "reference_like_link_count": reference_count,
        "numeric_claim_count": numeric_count,
        "qa_pair_count": qa_count,
        "methodology_language_count": methodology_count,
        "schema_type_count": schema_count,
        "content_family": family,
    }
    return RankedPage(page=page, score=score, family=family, reasons=reasons, signals=signals)


def internal_inbound_counts(pages: list[PageExtract]) -> Counter[str]:
    candidate_urls = {normalize_url(page.url) for page in pages}
    counts: Counter[str] = Counter()
    for page in pages:
        links = (page.evidence or {}).get("links", {}).get("internal_urls", [])
        for link in {normalize_url(url) for url in links}:
            if link in candidate_urls and link != normalize_url(page.url):
                counts[link] += 1
    return counts


def is_analyzable_unique_page(page: PageExtract) -> bool:
    return bool(
        page.status_code is not None
        and 200 <= page.status_code < 300
        and page.body_text
        and not page.is_duplicate
        and page.extraction_method in {"http", "browser"}
    )


def page_matches_url(page: PageExtract, url: str) -> bool:
    requested = (page.evidence or {}).get("identity", {}).get("requested_url")
    identities = {normalize_url(page.url)}
    if requested:
        identities.add(normalize_url(requested))
    return normalize_url(url) in identities


def valid_same_site_canonical(page: PageExtract) -> bool:
    if not page.canonical_url:
        return False
    return (urlparse(page.canonical_url).hostname or "").lower() == (
        urlparse(page.url).hostname or ""
    ).lower()


def richness_word_points(word_count: int) -> int:
    if word_count >= 1000:
        return 25
    if word_count >= 500:
        return 20
    if word_count >= 250:
        return 14
    if word_count >= 100:
        return 8
    if word_count >= 40:
        return 3
    return 0


def selection_reasons(**signals) -> tuple[str, ...]:
    reasons: list[str] = []
    if signals["is_audited"]:
        reasons.append("Explicitly audited URL")
    if signals["is_homepage"]:
        reasons.append("Site homepage")
    if signals["from_homepage"]:
        reasons.append("Linked directly from the homepage")
    if signals["inbound_count"] >= 2:
        reasons.append(f"High internal-link prominence ({signals['inbound_count']} candidate pages link here)")
    if signals["word_count"] >= 250:
        reasons.append(f"Substantial explanatory content ({signals['word_count']} words)")
    elif signals["word_count"] >= 100:
        reasons.append(f"Meaningful extracted content ({signals['word_count']} words)")
    if signals["explanatory"]:
        reasons.append("Explanatory content detected")
    if signals["numeric_count"]:
        reasons.append(f"Quantitative evidence detected ({signals['numeric_count']} statements)")
    if signals["reference_count"]:
        reasons.append(f"Reference-like citations detected ({signals['reference_count']} links)")
    if signals["has_authorship"]:
        reasons.append("Authorship provenance detected")
    if signals["schema_count"]:
        reasons.append(f"Structured data detected ({signals['schema_count']} schema types)")
    if signals["qa_count"]:
        reasons.append(f"Question-and-answer evidence detected ({signals['qa_count']} pairs)")
    if signals["methodology_count"]:
        reasons.append("Research or methodology evidence detected")
    if signals["comparison"]:
        reasons.append("Comparison-style explanatory content detected")
    return tuple(reasons[:8])
