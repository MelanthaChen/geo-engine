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


def build_recommendations(
    pages: list[PageExtract],
    *,
    requested_urls: int,
    accepted_html_responses: int,
) -> list[AuditRecommendation]:
    """Build opportunities only from directly measured page and crawl defects."""
    if not pages:
        return []

    recommendations: list[AuditRecommendation] = []
    analyzed_count = len(pages)

    recommendations.extend(build_faq_structure_opportunity(pages))

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
    )]


def explanatory_content_detected(page: PageExtract) -> bool:
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
    )]
