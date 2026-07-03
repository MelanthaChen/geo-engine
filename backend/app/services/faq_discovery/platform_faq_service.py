from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
import json
import logging
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from typing import Protocol
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
    hashtags: list[str] | None = None
    score: int | None = None
    engagement_metrics: dict | None = None
    created_at: datetime | None = None
    retrieval_method: str | None = None
    raw_metadata: dict | None = None


class PlatformDiscoveryProvider(Protocol):
    platform: str

    def retrieve(
        self,
        category: str,
        db: Session,
        property_id: int | None,
    ) -> list[RetrievedPlatformQuestion]:
        ...


class RedditDiscoveryProvider:
    platform = "reddit"

    def retrieve(
        self,
        category: str,
        db: Session,
        property_id: int | None,
    ) -> list[RetrievedPlatformQuestion]:
        return fetch_reddit_questions(category)


class XiaohongshuDiscoveryProvider:
    platform = "xiaohongshu"
    max_attempts = 2

    def retrieve(
        self,
        category: str,
        db: Session,
        property_id: int | None,
    ) -> list[RetrievedPlatformQuestion]:
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                questions = run_xiaohongshu_external_retrieval(category)

                if questions:
                    return questions
            except Exception as error:
                last_error = error
                logger.warning(
                    "[PLATFORM DISCOVERY] xiaohongshu retrieval attempt "
                    "%s/%s failed: %s",
                    attempt,
                    self.max_attempts,
                    error,
                )

        cached_questions = load_cached_platform_questions(
            db=db,
            property_id=property_id,
            platform="xiaohongshu",
            category=category,
            limit=settings.XIAOHONGSHU_RETRIEVAL_LIMIT,
        )

        if cached_questions:
            logger.info(
                "[PLATFORM DISCOVERY] xiaohongshu using cached results "
                "after retrieval failure."
            )
            return cached_questions

        logger.warning(
            "[PLATFORM DISCOVERY] xiaohongshu falling back to synthetic "
            "strategy topics. Last retrieval error: %s",
            last_error,
        )
        return build_xiaohongshu_note_topics(
            category=category,
            fallback_reason=str(last_error or "external retrieval unavailable"),
        )


def discover_platform_faqs(
    db: Session,
    category: str,
    website_url: str | None,
    property_id: int | None = None,
    publish_platform: str = "reddit",
):
    retrieved_questions = collect_external_platform_questions(
        db=db,
        category=category,
        property_id=property_id,
        publish_platform=publish_platform,
    )
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
    db: Session,
    category: str,
    property_id: int | None = None,
    publish_platform: str = "reddit",
) -> list[RetrievedPlatformQuestion]:
    provider = get_platform_discovery_provider(publish_platform)

    return provider.retrieve(
        category=category,
        db=db,
        property_id=property_id,
    )


def get_platform_discovery_provider(publish_platform: str):
    normalized_platform = (
        publish_platform or "reddit"
    ).strip().lower()

    if normalized_platform == "reddit":
        return RedditDiscoveryProvider()

    if normalized_platform == "xiaohongshu":
        return XiaohongshuDiscoveryProvider()

    return WebDiscussionDiscoveryProvider()


class WebDiscussionDiscoveryProvider:
    platform = "web_discussions"

    def retrieve(
        self,
        category: str,
        db: Session,
        property_id: int | None,
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

        return questions


def build_xiaohongshu_note_topics(
    category: str,
    fallback_reason: str | None = None,
) -> list[RetrievedPlatformQuestion]:
    topic_templates = [
        f"{category} 新手最容易忽略的选择标准",
        f"{category} 使用前应该先想清楚的三个场景",
        f"{category} 对比时不要只看功能列表",
        f"{category} 适合学生/新手吗？先看这些取舍",
        f"{category} 从真实工作流角度怎么判断值不值得用",
        f"{category} 常见误区和避坑角度整理",
        f"{category} 免费方案和付费方案该怎么比较",
        f"{category} 如果只解决一个问题，应该优先解决什么",
    ]

    return [
        RetrievedPlatformQuestion(
            platform="xiaohongshu_strategy",
            title=title,
            body=(
                "Synthetic fallback platform-native note angle for "
                "Xiaohongshu. Real retrieval failed or was unavailable."
            ),
            url=None,
            author=None,
            hashtags=["#小红书选题", "#平台洞察"],
            score=None,
            engagement_metrics=None,
            created_at=None,
            retrieval_method="synthetic_fallback",
            raw_metadata={
                "fallback": True,
                "reason": fallback_reason,
            },
        )
        for title in topic_templates
    ]


def run_xiaohongshu_external_retrieval(
    category: str,
) -> list[RetrievedPlatformQuestion]:
    command_template = settings.XIAOHONGSHU_RETRIEVAL_COMMAND

    if not command_template:
        raise RuntimeError(
            "XIAOHONGSHU_RETRIEVAL_COMMAND is not configured. Configure a "
            "MediaCrawler wrapper command that writes normalized JSON/JSONL."
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "xiaohongshu_results.jsonl"
        session_path = resolve_xiaohongshu_session_path()
        command = render_retrieval_command(
            template=command_template,
            query=category,
            output_path=output_path,
            session_path=session_path,
            limit=settings.XIAOHONGSHU_RETRIEVAL_LIMIT,
        )

        logger.info(
            "[PLATFORM DISCOVERY] running xiaohongshu retrieval backend: %s",
            command[0] if command else "unknown",
        )
        result = subprocess.run(
            command,
            capture_output=True,
            cwd=None,
            text=True,
            timeout=settings.XIAOHONGSHU_RETRIEVAL_TIMEOUT_SECONDS,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Xiaohongshu retrieval backend failed with exit code "
                f"{result.returncode}: {result.stderr[-1200:]}"
            )

        payload_text = ""

        if output_path.exists():
            payload_text = output_path.read_text(encoding="utf-8")

        if not payload_text.strip():
            payload_text = result.stdout

        notes = parse_external_retrieval_payload(payload_text)

        return [
            normalize_xiaohongshu_external_note(note)
            for note in notes
            if normalize_external_title(note)
        ][:settings.XIAOHONGSHU_RETRIEVAL_LIMIT]


def render_retrieval_command(
    template: str,
    query: str,
    output_path: Path,
    session_path: Path | None,
    limit: int,
):
    rendered = template.format(
        query=query,
        output=str(output_path),
        session_path=str(session_path or ""),
        limit=limit,
    )

    return shlex.split(rendered)


def resolve_xiaohongshu_session_path():
    candidates = [
        settings.XIAOHONGSHU_SESSION_PATH,
        "sessions/xiaohongshu/storage_state.json",
        "storage/xiaohongshu/geo_productivity_lab.json",
        "xiaohongshu_state.json",
    ]

    for candidate in candidates:
        if not candidate:
            continue

        path = Path(candidate)

        if path.exists():
            return path

    return None


def parse_external_retrieval_payload(payload_text: str):
    payload_text = payload_text.strip()

    if not payload_text:
        return []

    try:
        payload = json.loads(payload_text)
        return extract_note_list(payload)
    except json.JSONDecodeError:
        notes = []

        for line in payload_text.splitlines():
            line = line.strip()

            if not line:
                continue

            try:
                notes.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug(
                    "[PLATFORM DISCOVERY] skipping non-JSON retrieval line: %s",
                    line[:200],
                )

        return notes


def extract_note_list(payload):
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    for key in ["notes", "items", "data", "results", "records"]:
        value = payload.get(key)

        if isinstance(value, list):
            return value

    nested_data = payload.get("data")

    if isinstance(nested_data, dict):
        return extract_note_list(nested_data)

    return []


def normalize_xiaohongshu_external_note(note: dict):
    title = normalize_external_title(note)
    body = first_present(
        note,
        [
            "body",
            "content",
            "desc",
            "description",
            "note_desc",
            "text",
        ],
    )
    hashtags = normalize_external_hashtags(note, body)
    engagement_metrics = normalize_external_engagement(note)

    return RetrievedPlatformQuestion(
        platform="xiaohongshu",
        title=title,
        body=clean_text(str(body or ""))[:4000] or None,
        url=first_present(note, ["url", "note_url", "web_url", "share_url"]),
        author=normalize_external_author(note),
        hashtags=hashtags,
        score=primary_engagement_score(engagement_metrics),
        engagement_metrics=engagement_metrics,
        created_at=parse_datetime(
            first_present(note, ["created_at", "time", "publish_time"])
        ),
        retrieval_method="external_xiaohongshu_backend",
        raw_metadata=note,
    )


def first_present(payload: dict, keys: list[str]):
    for key in keys:
        value = payload.get(key)

        if value not in (None, ""):
            return value

    return None


def normalize_external_title(note: dict):
    return clean_text(
        str(
            first_present(
                note,
                ["title", "display_title", "note_title", "name"],
            ) or ""
        )
    )


def normalize_external_author(note: dict):
    author = note.get("author") or note.get("user") or note.get("user_info")

    if isinstance(author, dict):
        return first_present(
            author,
            ["nickname", "name", "user_name", "username", "display_name"],
        )

    return str(author) if author else None


def normalize_external_hashtags(note: dict, body: str | None):
    raw_hashtags = (
        note.get("hashtags")
        or note.get("tags")
        or note.get("tag_list")
        or []
    )

    if isinstance(raw_hashtags, str):
        hashtags = re.findall(r"#[^\s#]+", raw_hashtags)
    elif isinstance(raw_hashtags, list):
        hashtags = [
            normalize_hashtag_item(item)
            for item in raw_hashtags
        ]
    else:
        hashtags = []

    hashtags.extend(
        re.findall(r"#[^\s#]+", body or "")
    )

    normalized = []

    for hashtag in hashtags:
        if hashtag and hashtag not in normalized:
            normalized.append(hashtag)

    return normalized


def normalize_hashtag_item(item):
    if isinstance(item, dict):
        item = first_present(item, ["name", "tag_name", "title"])

    value = str(item or "").strip()

    if not value:
        return ""

    return value if value.startswith("#") else f"#{value}"


def normalize_external_engagement(note: dict):
    engagement = note.get("engagement_metrics")

    if isinstance(engagement, dict):
        return engagement

    mapping = {
        "liked_count": ["liked_count", "like_count", "likes"],
        "collected_count": ["collected_count", "collect_count", "saves"],
        "comment_count": ["comment_count", "comments"],
        "share_count": ["share_count", "shares"],
    }

    return {
        key: parse_first_integer(str(first_present(note, aliases) or ""))
        for key, aliases in mapping.items()
        if first_present(note, aliases) is not None
    }


def primary_engagement_score(engagement_metrics: dict | None):
    if not engagement_metrics:
        return None

    for key in [
        "liked_count",
        "like_count",
        "likes",
        "collected_count",
        "comment_count",
    ]:
        value = engagement_metrics.get(key)

        if value is not None:
            return parse_first_integer(str(value))

    return None


def load_cached_platform_questions(
    db: Session,
    property_id: int | None,
    platform: str,
    category: str,
    limit: int,
) -> list[RetrievedPlatformQuestion]:
    query = db.query(PlatformQuestion).filter(
        PlatformQuestion.property_id == property_id,
        PlatformQuestion.platform == platform,
    )

    cached_rows = (
        query.order_by(PlatformQuestion.discovered_at.desc())
        .limit(limit)
        .all()
    )

    return [
        platform_question_to_retrieved_question(row, "cache")
        for row in cached_rows
    ]


def platform_question_to_retrieved_question(
    row: PlatformQuestion,
    retrieval_method: str,
):
    return RetrievedPlatformQuestion(
        platform=row.platform,
        title=row.title,
        body=row.body,
        url=row.url,
        author=row.author,
        hashtags=parse_json_field(row.hashtags, []),
        score=row.score,
        engagement_metrics=parse_json_field(row.engagement_metrics, {}),
        created_at=row.created_at,
        retrieval_method=retrieval_method,
        raw_metadata=parse_json_field(row.raw_metadata, {}),
    )


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
            hashtags=json.dumps(question.hashtags or []),
            score=question.score,
            engagement_metrics=json.dumps(question.engagement_metrics or {}),
            retrieval_method=question.retrieval_method,
            raw_metadata=json.dumps(question.raw_metadata or {}),
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
        "hashtags": parse_json_field(question.hashtags, []),
        "score": question.score,
        "engagement_metrics": parse_json_field(question.engagement_metrics, {}),
        "retrieval_method": question.retrieval_method,
        "raw_metadata": parse_json_field(question.raw_metadata, {}),
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


def parse_json_field(value: str | None, fallback):
    if not value:
        return fallback

    try:
        return json.loads(value)
    except Exception:
        return fallback


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
