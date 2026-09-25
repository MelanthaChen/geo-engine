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
