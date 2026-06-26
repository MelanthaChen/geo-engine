from dataclasses import dataclass

from app.services.website_audit.extractor import PageExtract


@dataclass
class AuditScores:
    content_coverage_score: int
    faq_coverage_score: int
    internal_linking_score: int
    website_structure_score: int
    brand_clarity_score: int
    trust_signals_score: int
    overall_geo_score: int


def score_website(pages: list[PageExtract]) -> AuditScores:
    successful_pages = [page for page in pages if page.status_code == 200]

    if not successful_pages:
        return AuditScores(
            content_coverage_score=0,
            faq_coverage_score=0,
            internal_linking_score=0,
            website_structure_score=0,
            brand_clarity_score=0,
            trust_signals_score=0,
            overall_geo_score=0,
        )

    total_words = sum(page.word_count for page in successful_pages)
    average_internal_links = (
        sum(page.internal_link_count for page in successful_pages)
        / len(successful_pages)
        if successful_pages
        else 0
    )
    paths = [page.url.lower() for page in successful_pages]
    text = " ".join(page.body_text for page in successful_pages).lower()

    content_coverage = clamp(
        20
        + min(len(successful_pages), 12) * 4
        + min(total_words // 400, 8) * 4
    )
    faq_coverage = clamp(
        score_presence(paths, text, ["faq", "question", "answer"], 35)
        + score_presence(paths, text, ["help", "docs", "guide"], 20)
        + min(text.count("?"), 20)
    )
    internal_linking = clamp(25 + int(min(average_internal_links, 12) * 6))
    website_structure = clamp(
        20
        + score_path_presence(paths, ["pricing"], 12)
        + score_path_presence(paths, ["features"], 12)
        + score_path_presence(paths, ["blog", "guide", "resources"], 12)
        + score_path_presence(paths, ["about"], 10)
        + score_path_presence(paths, ["faq", "help", "docs"], 14)
    )
    brand_clarity = clamp(
        20
        + sum(12 for page in successful_pages[:5] if page.h1)
        + sum(8 for page in successful_pages[:5] if page.meta_description)
    )
    trust_signals = clamp(
        15
        + score_presence(
            paths,
            text,
            ["privacy", "terms", "security", "testimonial", "customer"],
            45,
        )
        + score_path_presence(paths, ["about"], 15)
    )
    overall = round(
        (
            content_coverage * 0.22
            + faq_coverage * 0.18
            + internal_linking * 0.15
            + website_structure * 0.18
            + brand_clarity * 0.17
            + trust_signals * 0.10
        )
    )

    return AuditScores(
        content_coverage_score=content_coverage,
        faq_coverage_score=faq_coverage,
        internal_linking_score=internal_linking,
        website_structure_score=website_structure,
        brand_clarity_score=brand_clarity,
        trust_signals_score=trust_signals,
        overall_geo_score=clamp(overall),
    )


def score_presence(
    paths: list[str],
    text: str,
    keywords: list[str],
    score: int,
) -> int:
    return score if any(keyword in text or keyword in " ".join(paths) for keyword in keywords) else 0


def score_path_presence(paths: list[str], keywords: list[str], score: int) -> int:
    return score if any(any(keyword in path for keyword in keywords) for path in paths) else 0


def clamp(value: float | int) -> int:
    return max(0, min(100, int(value)))
