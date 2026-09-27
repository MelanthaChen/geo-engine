from dataclasses import dataclass

from app.services.website_audit.extractor import PageExtract


@dataclass
class AuditRecommendation:
    category: str
    title: str
    description: str
    priority: str
    observed_evidence: str
    affected_page_count: int
    evaluated_page_count: int
    why_it_matters: str
    evidence_url: str | None = None
    affected_urls: list[str] | None = None
    suggested_strategy: str | None = None


def build_recommendations(
    pages: list[PageExtract],
    *,
    requested_urls: int,
    accepted_html_responses: int,
    all_pages: list[PageExtract] | None = None,
) -> list[AuditRecommendation]:
    """Build opportunities only from directly measured page and crawl defects."""
    if not pages:
        return []

    recommendations: list[AuditRecommendation] = []
    analyzed_count = len(pages)

    recommendations.extend(build_faq_structure_opportunity(pages))
    recommendations.extend(build_statistics_opportunity(pages))
    recommendations.extend(build_citation_opportunity(pages))
    recommendations.extend(build_authoritative_opportunity(pages))

    recommendations.extend(build_missing_field_opportunity(
        pages=pages,
        field="h1",
        category="heading_structure",
        title="Add missing H1 headings",
        observed_label="have no detected H1",
        why=(
            "An H1 identifies the primary page topic for readers and parsers; "
            "the appropriate wording still depends on each page's purpose."
        ),
    ))
    recommendations.extend(build_missing_field_opportunity(
        pages=pages,
        field="meta_description",
        category="metadata_coverage",
        title="Add missing meta descriptions",
        observed_label="have no detected meta description",
        why=(
            "A meta description provides an explicit page summary to systems that "
            "consume metadata, without assuming any particular business model."
        ),
    ))
    recommendations.extend(build_missing_field_opportunity(
        pages=pages,
        field="page_title",
        category="metadata_coverage",
        title="Add missing page titles",
        observed_label="have no detected title",
        why="A title supplies a basic document identifier for browsers, users, and parsers.",
    ))

    unsuccessful_html = max(requested_urls - accepted_html_responses, 0)
    if unsuccessful_html:
        affected_html_urls = [
            page.url for page in (all_pages or [])
            if not page.evidence.get("identity", {}).get("http_html_accepted", False)
        ]
        evidence = (
            f"{unsuccessful_html} of {requested_urls} requested URLs did not return "
            "a successful accepted HTML response."
        )
        recommendations.append(AuditRecommendation(
            category="http_html_success",
            title="Review URLs without successful HTML responses",
            description=evidence,
            priority="high",
            observed_evidence=evidence,
            affected_page_count=unsuccessful_html,
            evaluated_page_count=requested_urls,
            why_it_matters=(
                "Pages without successful HTML responses cannot contribute extracted content "
                "evidence to this audit and may be inaccessible to plain HTTP clients."
            ),
            evidence_url=affected_html_urls[0] if affected_html_urls else None,
            affected_urls=affected_html_urls,
        ))

    low_link_pages = [
        page for page in pages
        if page.word_count >= 150 and page.internal_link_count < 3
    ]
    if low_link_pages:
        evidence = (
            f"{len(low_link_pages)} of {analyzed_count} analyzed pages contain at least "
            "150 words and fewer than 3 detected internal links."
        )
        recommendations.append(AuditRecommendation(
            category="internal_linking_suggestions",
            title="Review pages with limited internal links",
            description=evidence,
            priority="medium",
            observed_evidence=evidence,
            affected_page_count=len(low_link_pages),
            evaluated_page_count=analyzed_count,
            why_it_matters=(
                "Relevant internal links can give readers and crawlers explicit paths to "
                "related content; whether a link belongs must be judged page by page."
            ),
            evidence_url=low_link_pages[0].url,
            affected_urls=[page.url for page in low_link_pages],
        ))

    return recommendations


def build_faq_structure_opportunity(pages: list[PageExtract]) -> list[AuditRecommendation]:
    """Recommend Q&A restructuring only from measured content evidence."""
    strong_faq_pages = [
        page for page in pages
        if page.faq_page_schema_detected
        or page.detected_qa_pair_count >= 2
        or (page.faq_like_heading_count > 0 and page.question_heading_count >= 2)
    ]
    candidates = [
        page for page in pages
        if page not in strong_faq_pages
        and page.word_count >= 250
        and explanatory_content_detected(page)
        and page.question_heading_count < 2
        and page.detected_qa_pair_count == 0
        and not page.faq_page_schema_detected
    ]
    if not candidates:
        return []

    # A site with an already-strong FAQ area is not prioritized for FAQ merely
    # because another isolated page could be reformatted. A recommendation is
    # still warranted when several or most explanatory pages lack Q&A structure.
    if strong_faq_pages and len(candidates) < max(3, (len(pages) + 1) // 2):
        return []

    question_headings = sum(page.question_heading_count for page in candidates)
    evidence = (
        f"{len(candidates)} of {len(pages)} analyzed pages contain at least 250 words "
        "and explanatory or how-to language, but have no detected FAQPage schema, "
        f"no detected Q&A pairs, and only {question_headings} question-style headings."
    )
    return [AuditRecommendation(
        category="faq_opportunities",
        title="Consider explicit FAQ / Q&A structure",
        description=evidence,
        priority="medium",
        observed_evidence=evidence,
        affected_page_count=len(candidates),
        evaluated_page_count=len(pages),
        why_it_matters=(
            "Explicit questions paired with answers can make information easier to identify "
            "and extract, while the answers must remain grounded in the existing page content."
        ),
        evidence_url=candidates[0].url,
        affected_urls=[page.url for page in candidates],
        suggested_strategy="faq",
    )]


def build_statistics_opportunity(pages: list[PageExtract]) -> list[AuditRecommendation]:
    candidates = [
        page for page in pages
        if page.word_count >= 250
        and explanatory_content_detected(page)
        and page_strategy(page, "statistics").get("numeric_claim_count", 0) <= 1
    ]
    if len(candidates) < min_required_candidates(len(pages)):
        return []
    total_claims = sum(
        page_strategy(page, "statistics").get("numeric_claim_count", 0)
        for page in candidates
    )
    evidence = (
        f"{len(candidates)} of {len(pages)} analyzed pages contain at least 250 words "
        "and explanatory language, while those pages contain only "
        f"{total_claims} detected numeric claims in total."
    )
    return [AuditRecommendation(
        category="statistics",
        title="Review explanatory pages with little quantitative evidence",
        description=evidence,
        priority="medium",
        observed_evidence=evidence,
        affected_page_count=len(candidates),
        evaluated_page_count=len(pages),
        why_it_matters=(
            "Grounded quantitative facts may make factual explanations more specific, but "
            "only verified figures appropriate to each page should be added."
        ),
        evidence_url=candidates[0].url,
        affected_urls=[page.url for page in candidates],
        suggested_strategy="statistics",
    )]


def build_citation_opportunity(pages: list[PageExtract]) -> list[AuditRecommendation]:
    candidates = [
        page for page in pages
        if page.word_count >= 250
        and explanatory_content_detected(page)
        and page_strategy(page, "citation").get("reference_like_link_count", 0) == 0
        and page_strategy(page, "citation").get("attribution_phrase_count", 0) == 0
    ]
    if len(candidates) < min_required_candidates(len(pages)):
        return []
    evidence = (
        f"{len(candidates)} of {len(pages)} analyzed pages contain at least 250 words "
        "and explanatory language, but contain no detected reference-like outbound links "
        "or source-attribution phrases."
    )
    return [AuditRecommendation(
        category="citation",
        title="Review informational pages with limited source attribution",
        description=evidence,
        priority="medium",
        observed_evidence=evidence,
        affected_page_count=len(candidates),
        evaluated_page_count=len(pages),
        why_it_matters=(
            "Explicit links to relevant primary sources can make factual provenance inspectable; "
            "citations are not assumed to be appropriate for every page."
        ),
        evidence_url=candidates[0].url,
        affected_urls=[page.url for page in candidates],
        suggested_strategy="citation",
    )]


def build_authoritative_opportunity(pages: list[PageExtract]) -> list[AuditRecommendation]:
    candidates = []
    for page in pages:
        authority = page_strategy(page, "authoritative")
        if (
            page.word_count >= 250
            and explanatory_content_detected(page)
            and not authority.get("named_author_present")
            and not authority.get("published_or_modified_date_present")
            and authority.get("reference_like_link_count", 0) == 0
        ):
            candidates.append(page)
    if len(candidates) < min_required_candidates(len(pages)):
        return []
    evidence = (
        f"{len(candidates)} of {len(pages)} analyzed informational pages contain at least "
        "250 words but expose no detected named author, publication/update date, or "
        "reference-like outbound link."
    )
    return [AuditRecommendation(
        category="authoritative",
        title="Review explicit authorship and source provenance",
        description=evidence,
        priority="medium",
        observed_evidence=evidence,
        affected_page_count=len(candidates),
        evaluated_page_count=len(pages),
        why_it_matters=(
            "Explicit, truthful authorship and source provenance can help readers inspect who "
            "produced informational content and what evidence it relies on."
        ),
        evidence_url=candidates[0].url,
        affected_urls=[page.url for page in candidates],
        suggested_strategy="authoritative",
    )]


def explanatory_content_detected(page: PageExtract) -> bool:
    faq = page_strategy(page, "faq")
    if faq:
        return bool(faq.get("explanatory_text_present"))
    text = " ".join(filter(None, [
        page.page_title,
        page.h1,
        page.meta_description,
        page.body_text,
    ])).lower()
    return any(term in text for term in (
        "how ", "what ", "why ", "guide", "step", "learn", "help",
        "explain", "understand", "works", "allows", "provides",
    ))


def page_strategy(page: PageExtract, name: str) -> dict:
    return page.evidence.get("strategies", {}).get(name, {})


def min_required_candidates(page_count: int) -> int:
    return 1 if page_count == 1 else max(2, (page_count + 2) // 3)


def build_missing_field_opportunity(
    *,
    pages: list[PageExtract],
    field: str,
    category: str,
    title: str,
    observed_label: str,
    why: str,
) -> list[AuditRecommendation]:
    affected = [page for page in pages if not getattr(page, field)]
    if not affected:
        return []

    evidence = f"{len(affected)} of {len(pages)} analyzed pages {observed_label}."
    return [AuditRecommendation(
        category=category,
        title=title,
        description=evidence,
        priority="high" if len(affected) == len(pages) else "medium",
        observed_evidence=evidence,
        affected_page_count=len(affected),
        evaluated_page_count=len(pages),
        why_it_matters=why,
        evidence_url=affected[0].url,
        affected_urls=[page.url for page in affected],
    )]
