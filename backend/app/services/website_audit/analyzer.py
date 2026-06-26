from dataclasses import dataclass

from app.services.website_audit.extractor import PageExtract


AUDIENCE_KEYWORDS = {
    "students": ["student", "campus", "college", "university"],
    "job seekers": ["resume", "job seeker", "interview", "career", "ats"],
    "founders": ["startup", "founder", "launch", "product"],
    "teams": ["team", "collaboration", "workspace", "organization"],
    "developers": ["developer", "api", "docs", "github", "code"],
    "researchers": ["research", "analysis", "citation", "paper"],
    "marketers": ["marketing", "seo", "content", "campaign"],
}

USE_CASE_KEYWORDS = {
    "comparison and selection": ["compare", "alternative", "versus", "vs"],
    "getting started": ["start", "setup", "create", "build", "generate"],
    "pricing evaluation": ["pricing", "plan", "free", "cost"],
    "workflow improvement": ["workflow", "template", "automate", "process"],
    "trust evaluation": ["security", "privacy", "testimonial", "case study"],
    "learning and guidance": ["guide", "faq", "docs", "learn", "examples"],
}


@dataclass
class BrandUnderstanding:
    brand_summary: str
    product_summary: str
    target_audience: str
    primary_use_cases: str
    core_value_proposition: str


def analyze_brand_understanding(
    pages: list[PageExtract],
    property_name: str,
    brand_name: str | None,
) -> BrandUnderstanding:
    homepage = find_homepage(pages)
    key_pages = sorted(
        pages,
        key=lambda page: (
            page.status_code != 200,
            -page.word_count,
        ),
    )[:5]
    combined_text = " ".join(page.body_text for page in key_pages).lower()
    display_brand = brand_name or property_name

    product_summary = first_available(
        homepage.h1 if homepage else None,
        homepage.meta_description if homepage else None,
        homepage.page_title if homepage else None,
        f"{display_brand} website",
    )

    target_audience = infer_target_audience(combined_text)
    primary_use_cases = infer_primary_use_cases(combined_text)
    value_prop = infer_value_proposition(homepage, display_brand)

    return BrandUnderstanding(
        brand_summary=(
            f"{display_brand} appears to present itself as {product_summary}."
        ),
        product_summary=product_summary,
        target_audience=target_audience,
        primary_use_cases=primary_use_cases,
        core_value_proposition=value_prop,
    )


def find_homepage(pages: list[PageExtract]) -> PageExtract | None:
    for page in pages:
        path = page.url.rstrip("/").split("/")[-1]

        if not path or path == page.url.split("//")[-1].split("/")[0]:
            return page

    return pages[0] if pages else None


def infer_target_audience(text: str) -> str:
    matches = [
        audience
        for audience, keywords in AUDIENCE_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]

    if matches:
        return ", ".join(matches[:3])

    return "general website visitors evaluating the product or category"


def infer_primary_use_cases(text: str) -> str:
    matches = [
        use_case
        for use_case, keywords in USE_CASE_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]

    if matches:
        return ", ".join(matches[:4])

    return "understanding the product, evaluating fit, and learning next steps"


def infer_value_proposition(
    homepage: PageExtract | None,
    brand_name: str,
) -> str:
    if homepage and homepage.meta_description:
        return homepage.meta_description

    if homepage and homepage.h1:
        return homepage.h1

    return f"{brand_name} needs clearer homepage messaging for AI systems."


def first_available(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()

    return ""
