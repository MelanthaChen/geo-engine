from dataclasses import dataclass

from app.services.website_audit.extractor import PageExtract
from app.services.website_audit.scoring import AuditScores


@dataclass
class AuditRecommendation:
    category: str
    title: str
    description: str
    priority: str
    evidence_url: str | None = None


IMPORTANT_PAGE_RULES = [
    ("missing_pages", "Pricing", ["pricing", "plans"]),
    ("missing_pages", "FAQ", ["faq", "questions"]),
    ("missing_pages", "Comparison pages", ["compare", "comparison", "versus", "vs"]),
    ("missing_pages", "Examples", ["examples", "showcase"]),
    ("missing_pages", "Templates", ["templates"]),
    ("missing_pages", "Documentation", ["docs", "documentation", "help"]),
]

GEO_TOPIC_RULES = [
    ("missing_geo_topics", "Category comparison", ["alternative", "compare", "versus"]),
    ("missing_geo_topics", "Use-case pages", ["use case", "workflow", "for students", "for teams"]),
    ("missing_geo_topics", "Decision criteria", ["criteria", "checklist", "how to choose"]),
    ("missing_geo_topics", "Limitations and tradeoffs", ["limitation", "tradeoff", "drawback"]),
    ("missing_geo_topics", "Trust and privacy", ["privacy", "security", "data"]),
]

FAQ_RULES = [
    ("What problem does this product solve?", ["problem", "solve"]),
    ("Who is this product best suited for?", ["who", "audience"]),
    ("How does pricing work?", ["pricing", "plan", "cost"]),
    ("How does it compare with common alternatives?", ["compare", "alternative"]),
    ("What limitations should buyers understand?", ["limitation", "tradeoff"]),
]


def build_recommendations(
    pages: list[PageExtract],
    scores: AuditScores,
    category_hint: str,
) -> list[AuditRecommendation]:
    recommendations: list[AuditRecommendation] = []
    paths_and_text = build_search_text(pages)

    recommendations.extend(detect_missing_pages(paths_and_text))
    recommendations.extend(detect_missing_geo_topics(paths_and_text, category_hint))
    recommendations.extend(build_internal_linking_suggestions(pages, scores))
    recommendations.extend(build_faq_opportunities(paths_and_text))
    recommendations.extend(build_content_recommendations(paths_and_text, category_hint))

    return recommendations


def detect_missing_pages(search_text: str) -> list[AuditRecommendation]:
    recommendations = []

    for category, title, keywords in IMPORTANT_PAGE_RULES:
        if any(keyword in search_text for keyword in keywords):
            continue

        recommendations.append(
            AuditRecommendation(
                category=category,
                title=f"Create a {title.lower()} page",
                description=(
                    f"The crawl did not find clear {title.lower()} coverage. "
                    "AI answer systems often rely on dedicated pages for "
                    "entity understanding and comparison-style retrieval."
                ),
                priority="high" if title in {"FAQ", "Comparison pages"} else "medium",
            )
        )

    return recommendations


def detect_missing_geo_topics(
    search_text: str,
    category_hint: str,
) -> list[AuditRecommendation]:
    recommendations = []

    for category, title, keywords in GEO_TOPIC_RULES:
        if any(keyword in search_text for keyword in keywords):
            continue

        recommendations.append(
            AuditRecommendation(
                category=category,
                title=title,
                description=(
                    f"Add content about {title.lower()} for {category_hint}. "
                    "This improves information gain for AI systems answering "
                    "category-level questions."
                ),
                priority="medium",
            )
        )

    return recommendations


def build_internal_linking_suggestions(
    pages: list[PageExtract],
    scores: AuditScores,
) -> list[AuditRecommendation]:
    successful_pages = [page for page in pages if page.status_code == 200]
    recommendations = []

    weak_pages = [
        page
        for page in successful_pages
        if page.word_count >= 150 and page.internal_link_count < 3
    ]

    for page in weak_pages[:5]:
        recommendations.append(
            AuditRecommendation(
                category="internal_linking_suggestions",
                title="Add contextual internal links",
                description=(
                    "This page has useful text but few internal links. Add "
                    "links to related FAQs, comparison pages, pricing, or "
                    "examples so crawlers can connect the topic graph."
                ),
                priority="medium",
                evidence_url=page.url,
            )
        )

    if scores.internal_linking_score < 55 and not recommendations:
        recommendations.append(
            AuditRecommendation(
                category="internal_linking_suggestions",
                title="Strengthen the site's internal topic graph",
                description=(
                    "The crawl found limited internal linking. Link core "
                    "landing pages to FAQ, examples, guides, and comparison "
                    "content using descriptive anchor text."
                ),
                priority="high",
            )
        )

    return recommendations


def build_faq_opportunities(search_text: str) -> list[AuditRecommendation]:
    recommendations = []

    for question, keywords in FAQ_RULES:
        if any(keyword in search_text for keyword in keywords):
            continue

        recommendations.append(
            AuditRecommendation(
                category="faq_opportunities",
                title=question,
                description=(
                    "Add a concise answer backed by website-specific evidence. "
                    "This creates extractable information for AI answer engines."
                ),
                priority="medium",
            )
        )

    return recommendations


def build_content_recommendations(
    search_text: str,
    category_hint: str,
) -> list[AuditRecommendation]:
    base_recommendations = [
        (
            "Comparison page",
            f"Create a comparison page for common {category_hint} alternatives.",
            ["compare", "alternative"],
            "high",
        ),
        (
            "Buying guide",
            f"Create a practical buying guide for evaluating {category_hint}.",
            ["buying guide", "how to choose"],
            "medium",
        ),
        (
            "Educational article",
            f"Create an educational article explaining common {category_hint} workflows.",
            ["guide", "workflow"],
            "medium",
        ),
        (
            "Evidence page",
            "Create a page with examples, screenshots, methodology, or proof points.",
            ["example", "case study", "testimonial"],
            "medium",
        ),
    ]

    recommendations = []

    for title, description, keywords, priority in base_recommendations:
        if any(keyword in search_text for keyword in keywords):
            continue

        recommendations.append(
            AuditRecommendation(
                category="content_recommendations",
                title=title,
                description=description,
                priority=priority,
            )
        )

    return recommendations


def build_search_text(pages: list[PageExtract]) -> str:
    return " ".join(
        " ".join(
            [
                page.url,
                page.page_title or "",
                page.meta_description or "",
                page.h1 or "",
                page.body_text[:3000],
            ]
        )
        for page in pages
        if page.status_code == 200
    ).lower()
