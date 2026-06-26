from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
import logging
import re
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.platform_question import PlatformQuestion
from app.services.history.faq_history_service import create_faq_set


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = (
    "GEOEnginePlatformDiscovery/1.0 "
    "(research retrieval; contact: local-development)"
)
UNSUPPORTED_PLATFORM_REASONS = {
    "product_hunt": (
        "Product Hunt discovery requires the official Product Hunt API and "
        "OAuth credentials; no approved public feed is configured."
    ),
    "quora": "Quora does not provide an approved public search API.",
    "medium": "Medium does not provide an approved public discussion search API.",
    "x": "X/Twitter discovery requires an approved API integration.",
    "xiaohongshu": (
        "Xiaohongshu discovery requires an approved API or licensed data "
        "source."
    ),
}


@dataclass
class RetrievedPlatformQuestion:
    platform: str
    title: str
    body: str | None = None
    url: str | None = None
    author: str | None = None
    score: int | None = None
    created_at: datetime | None = None


def discover_platform_faqs(
    db: Session,
    category: str,
    website_url: str | None,
    property_id: int | None = None,
):
    retrieved_questions = collect_external_platform_questions(category)
    saved_questions = save_platform_questions(
        db=db,
        property_id=property_id,
        questions=retrieved_questions,
    )

    faq_set = create_faq_set(
        db=db,
        property_id=property_id,
        category=category,
        faq_source="PLATFORM",
        questions=[question.title for question in saved_questions[:20]],
        website_url=website_url,
    )
    setattr(faq_set, "_platform_questions", saved_questions)

    return faq_set


def collect_external_platform_questions(
    category: str,
) -> list[RetrievedPlatformQuestion]:
    questions: list[RetrievedPlatformQuestion] = []

    collectors = [
        ("reddit", fetch_reddit_questions),
        ("github_discussions", fetch_github_discussion_questions),
        ("github_issues", fetch_github_issue_questions),
        ("hacker_news", fetch_hacker_news_questions),
        ("stack_overflow", fetch_stack_overflow_questions),
    ]

    for platform, collector in collectors:
        try:
            questions.extend(collector(category))
        except Exception as error:
            logger.warning(
                "[PLATFORM DISCOVERY] %s discovery failed: %s",
                platform,
                error,
            )

    for platform, reason in UNSUPPORTED_PLATFORM_REASONS.items():
        logger.info(
            "[PLATFORM DISCOVERY] %s unsupported: %s",
            platform,
            reason,
        )

    return questions


def fetch_reddit_questions(category: str) -> list[RetrievedPlatformQuestion]:
    url = (
        "https://old.reddit.com/search/"
        f"?q={quote_plus(category)}&sort=relevance&t=all"
    )
    response = requests.get(url, headers=request_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result in soup.select(".search-result")[:15]:
        title_link = result.select_one("a.search-title")

        if not title_link:
            continue

        title = clean_text(title_link.get_text(" ", strip=True))

        if not looks_like_question_or_discussion(title):
            continue

        body_node = result.select_one(".search-expando")
        author_node = result.select_one(".search-author a")
        score_node = result.select_one(".search-score")
        timestamp_node = result.select_one("time")

        results.append(
            RetrievedPlatformQuestion(
                platform="reddit",
                title=title,
                body=clean_text(body_node.get_text(" ", strip=True))
                if body_node
                else None,
                url=absolute_reddit_url(title_link.get("href")),
                author=clean_text(author_node.get_text(" ", strip=True))
                if author_node
                else None,
                score=parse_first_integer(
                    score_node.get_text(" ", strip=True)
                    if score_node
                    else ""
                ),
                created_at=parse_datetime(
                    timestamp_node.get("datetime")
                    if timestamp_node
                    else None
                ),
            )
        )

    return results


def fetch_github_discussion_questions(
    category: str,
) -> list[RetrievedPlatformQuestion]:
    if not settings.GITHUB_TOKEN:
        logger.info(
            "[PLATFORM DISCOVERY] github_discussions unsupported: "
            "GitHub Discussions discovery requires GITHUB_TOKEN for "
            "authenticated GraphQL search."
        )
        return []

    query = """
    query($query: String!) {
      search(query: $query, type: DISCUSSION, first: 15) {
        nodes {
          ... on Discussion {
            title
            bodyText
            url
            createdAt
            upvoteCount
            author {
              login
            }
          }
        }
      }
    }
    """
    response = requests.post(
        "https://api.github.com/graphql",
        headers={
            **request_headers(),
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        },
        json={"query": query, "variables": {"query": category}},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()

    if payload.get("errors"):
        logger.warning(
            "[PLATFORM DISCOVERY] github_discussions GraphQL errors: %s",
            payload["errors"],
        )
        return []

    questions = []

    for item in payload.get("data", {}).get("search", {}).get("nodes", []):
        title = clean_text(item.get("title", ""))

        if not looks_like_question_or_discussion(title):
            continue

        author = item.get("author") or {}
        questions.append(
            RetrievedPlatformQuestion(
                platform="github_discussions",
                title=title,
                body=clean_text(item.get("bodyText") or "")[:1200] or None,
                url=item.get("url"),
                author=author.get("login"),
                score=item.get("upvoteCount"),
                created_at=parse_datetime(item.get("createdAt")),
            )
        )

    return questions


def fetch_github_issue_questions(
    category: str,
) -> list[RetrievedPlatformQuestion]:
    url = (
        "https://api.github.com/search/issues"
        f"?q={quote_plus(category)}+is:issue&sort=comments&order=desc"
    )
    response = requests.get(url, headers=request_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    questions = []

    for item in response.json().get("items", [])[:15]:
        if "pull_request" in item:
            continue

        title = clean_text(item.get("title", ""))

        if not looks_like_question_or_discussion(title):
            continue

        questions.append(
            RetrievedPlatformQuestion(
                platform="github_issues",
                title=title,
                body=clean_text(item.get("body") or "")[:1200] or None,
                url=item.get("html_url"),
                author=(item.get("user") or {}).get("login"),
                score=item.get("comments"),
                created_at=parse_datetime(item.get("created_at")),
            )
        )

    return questions


def fetch_hacker_news_questions(
    category: str,
) -> list[RetrievedPlatformQuestion]:
    url = (
        "https://hn.algolia.com/api/v1/search"
        f"?query={quote_plus(category)}&tags=story"
    )
    response = requests.get(url, headers=request_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    questions = []

    for hit in response.json().get("hits", [])[:15]:
        title = clean_text(hit.get("title") or hit.get("story_title") or "")

        if not looks_like_question_or_discussion(title):
            continue

        object_id = hit.get("objectID")
        questions.append(
            RetrievedPlatformQuestion(
                platform="hacker_news",
                title=title,
                body=None,
                url=(
                    f"https://news.ycombinator.com/item?id={object_id}"
                    if object_id
                    else hit.get("url")
                ),
                author=hit.get("author"),
                score=hit.get("points") or hit.get("num_comments"),
                created_at=parse_datetime(hit.get("created_at")),
            )
        )

    return questions


def fetch_stack_overflow_questions(
    category: str,
) -> list[RetrievedPlatformQuestion]:
    url = (
        "https://api.stackexchange.com/2.3/search/advanced"
        f"?order=desc&sort=relevance&q={quote_plus(category)}"
        "&site=stackoverflow"
    )
    response = requests.get(url, headers=request_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    questions = []

    for item in response.json().get("items", [])[:15]:
        title = clean_text(html.unescape(item.get("title", "")))

        if not title:
            continue

        questions.append(
            RetrievedPlatformQuestion(
                platform="stack_overflow",
                title=title,
                body=None,
                url=item.get("link"),
                author=(item.get("owner") or {}).get("display_name"),
                score=item.get("score"),
                created_at=parse_epoch(item.get("creation_date")),
            )
        )

    return questions


def save_platform_questions(
    db: Session,
    property_id: int | None,
    questions: list[RetrievedPlatformQuestion],
) -> list[PlatformQuestion]:
    saved_questions: list[PlatformQuestion] = []
    seen_hashes: set[str] = set()

    for question in questions:
        normalized_title = normalize_text(question.title)
        content_hash = build_content_hash(
            property_id=property_id,
            title=normalized_title,
            body=question.body,
        )

        if content_hash in seen_hashes:
            continue

        seen_hashes.add(content_hash)

        existing = (
            db.query(PlatformQuestion)
            .filter(
                PlatformQuestion.property_id == property_id,
                PlatformQuestion.content_hash == content_hash,
            )
            .first()
        )

        if existing:
            saved_questions.append(existing)
            continue

        platform_question = PlatformQuestion(
            property_id=property_id,
            platform=question.platform,
            title=question.title,
            body=question.body,
            url=question.url,
            author=question.author,
            score=question.score,
            created_at=question.created_at,
            content_hash=content_hash,
        )
        db.add(platform_question)
        saved_questions.append(platform_question)

    db.commit()

    for question in saved_questions:
        db.refresh(question)

    return saved_questions


def serialize_platform_question(question: PlatformQuestion):
    return {
        "id": question.id,
        "property_id": question.property_id,
        "platform": question.platform,
        "title": question.title,
        "body": question.body,
        "url": question.url,
        "author": question.author,
        "score": question.score,
        "created_at": question.created_at,
        "discovered_at": question.discovered_at,
        "content_hash": question.content_hash,
    }


def request_headers():
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    }


def absolute_reddit_url(url: str | None):
    if not url:
        return None

    if url.startswith("http"):
        return url

    return f"https://old.reddit.com{url}"


def looks_like_question_or_discussion(title: str):
    normalized = title.lower()

    if "?" in title:
        return True

    discussion_markers = [
        "best",
        "vs",
        "versus",
        "alternative",
        "recommend",
        "looking for",
        "how do",
        "how to",
        "should i",
        "worth",
        "compare",
        "problem",
        "issue",
    ]

    return any(marker in normalized for marker in discussion_markers)


def build_content_hash(
    property_id: int | None,
    title: str,
    body: str | None,
):
    normalized_body = normalize_text(body or "")
    hash_input = f"{property_id or 'global'}::{title}::{normalized_body}"

    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def normalize_text(value: str):
    return re.sub(r"\s+", " ", value.strip().lower())


def clean_text(value: str):
    return re.sub(r"\s+", " ", value or "").strip()


def parse_first_integer(value: str):
    match = re.search(r"-?\d+", value or "")

    if not match:
        return None

    return int(match.group(0))


def parse_epoch(value):
    if value is None:
        return None

    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def parse_datetime(value: str | None):
    if not value:
        return None

    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None
