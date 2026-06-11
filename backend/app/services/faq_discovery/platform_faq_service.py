from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.faq_discovery.ai_faq_service import parse_questions
from app.services.history.faq_history_service import create_faq_set


client = OpenAI(api_key=settings.OPENAI_API_KEY)


def discover_platform_faqs(
    db: Session,
    category: str,
    website_url: str | None,
):
    crawled_text = crawl_website_text(website_url)

    prompt = f"""
You are a GEO research analyst.

Product category:
{category}

Website URL:
{website_url or "Not provided"}

Website content:
{crawled_text[:12000] or "No website content was available."}

Extract 10-20 question-style FAQ entries based only on actual website content.

Look for:
- FAQ sections
- help pages
- guides
- blog content
- product pages
- feature explanations
- workflow descriptions

Rules:
- Questions must be category-driven, not promotional.
- Do not invent features not present in the website content.
- If the website discusses ATS optimization, a valid question is:
  "How does ATS optimization work?"
- If the website discusses resume keywords, a valid question is:
  "What keywords should be included in a resume?"
- Return ranked FAQs only.

Format:
1. Question
2. Question
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract user questions from website content. "
                    "You do not invent unsupported claims."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.35
    )

    questions = parse_questions(
        response.choices[0].message.content
    )[:20]

    return create_faq_set(
        db=db,
        category=category,
        faq_source="PLATFORM",
        questions=questions,
        website_url=website_url,
    )


def crawl_website_text(
    website_url: str | None,
):
    if not website_url:
        return ""

    visited = set()
    to_visit = [website_url]
    collected_text = []
    root_domain = urlparse(website_url).netloc

    while to_visit and len(visited) < 6:
        url = to_visit.pop(0)

        if url in visited:
            continue

        visited.add(url)

        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 GEO Research Bot "
                        "(content discovery; non-indexing)"
                    )
                },
                timeout=12
            )
            response.raise_for_status()
        except Exception as error:
            print(f"[PLATFORM FAQ] Crawl failed for {url}: {error}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        page_text = " ".join(
            soup.get_text(" ").split()
        )

        if page_text:
            collected_text.append(page_text[:5000])

        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link["href"]).split("#")[0]
            parsed = urlparse(next_url)

            if parsed.netloc != root_domain:
                continue

            if next_url in visited or next_url in to_visit:
                continue

            if is_research_relevant_path(parsed.path):
                to_visit.append(next_url)

    return "\n\n".join(collected_text)


def is_research_relevant_path(path: str):
    normalized = path.lower()

    return (
        normalized in {"", "/"}
        or any(
            token in normalized
            for token in [
                "faq",
                "help",
                "guide",
                "blog",
                "learn",
                "resource",
                "feature",
                "pricing",
                "about",
            ]
        )
    )
