from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
import json
import logging
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
from typing import Protocol
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account import Account
from app.models.platform_question import PlatformQuestion
from app.services.history.faq_history_service import create_faq_set
from app.services.account_service import seed_demo_accounts
from app.services.publishing_service import select_publish_account
from app.services.session_resolver import SessionResolver


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
        account: Account | None = None,
    ) -> list[RetrievedPlatformQuestion]:
        ...


class RedditDiscoveryProvider:
    platform = "reddit"

    def retrieve(
        self,
        category: str,
        db: Session,
        property_id: int | None,
        account: Account | None = None,
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
        account: Account | None = None,
    ) -> list[RetrievedPlatformQuestion]:
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                questions = run_xiaohongshu_external_retrieval(
                    category=category,
                    account=account,
                )

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
                "[PLATFORM DISCOVERY] xiaohongshu using cached real results "
                "after retrieval failure."
            )
            return cached_questions

        raise RuntimeError(
            "Real Xiaohongshu retrieval failed and no cached real "
            f"Xiaohongshu notes are available. Last error: {last_error}"
        )


def discover_platform_faqs(
    db: Session,
    category: str,
    website_url: str | None,
    property_id: int | None = None,
    publish_platform: str = "reddit",
    account_id: int | None = None,
):
    selected_account = select_discovery_account(
        db=db,
        account_id=account_id,
        publish_platform=publish_platform,
        property_id=property_id,
    )
    retrieved_questions = collect_external_platform_questions(
        db=db,
        category=category,
        property_id=property_id,
        publish_platform=publish_platform,
        account=selected_account,
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
    account: Account | None = None,
) -> list[RetrievedPlatformQuestion]:
    provider = get_platform_discovery_provider(publish_platform)

    return provider.retrieve(
        category=category,
        db=db,
        property_id=property_id,
        account=account,
    )


def select_discovery_account(
    db: Session,
    account_id: int | None,
    publish_platform: str,
    property_id: int | None,
):
    normalized_platform = (publish_platform or "reddit").strip().lower()

    if normalized_platform != "xiaohongshu":
        return None

    account = select_publish_account(
        db=db,
        account_id=account_id,
        publish_platform=normalized_platform,
        property_id=property_id,
    )

    if not account and property_id is not None:
        seed_demo_accounts(db, property_id=property_id)
        account = select_publish_account(
            db=db,
            account_id=account_id,
            publish_platform=normalized_platform,
            property_id=property_id,
        )

    return account


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
        account: Account | None = None,
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


def run_xiaohongshu_external_retrieval(
    category: str,
    account: Account | None = None,
) -> list[RetrievedPlatformQuestion]:
    command_template = settings.XIAOHONGSHU_RETRIEVAL_COMMAND

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_path = Path(temp_dir) / "xiaohongshu_results.jsonl"
        mediacrawler_output_dir = temp_path / "mediacrawler_output"
        session_path = resolve_xiaohongshu_session_path(account=account)

        if command_template:
            command = render_retrieval_command(
                template=command_template,
                query=category,
                output_path=output_path,
                session_path=session_path,
                limit=settings.XIAOHONGSHU_RETRIEVAL_LIMIT,
                save_data_path=mediacrawler_output_dir,
            )
            cwd = None
            backend_name = "configured command"
        else:
            command = build_default_mediacrawler_command(
                query=category,
                save_data_path=mediacrawler_output_dir,
                limit=settings.XIAOHONGSHU_RETRIEVAL_LIMIT,
                session_path=session_path,
            )
            cwd = resolve_mediacrawler_path()
            backend_name = "MediaCrawler"

        logger.info(
            "[PLATFORM DISCOVERY] running xiaohongshu retrieval backend=%s "
            "query=%r limit=%s",
            backend_name,
            category,
            settings.XIAOHONGSHU_RETRIEVAL_LIMIT,
        )
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                cwd=cwd,
                text=True,
                timeout=settings.XIAOHONGSHU_RETRIEVAL_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode("utf-8", "replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = error.stderr.decode("utf-8", "replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
            raise RuntimeError(
                "Xiaohongshu retrieval timed out before returning real notes. "
                "This usually means MediaCrawler is waiting for a valid "
                "Xiaohongshu login/session or is blocked before search. "
                f"stdout={stdout[-800:]} stderr={stderr[-800:]}"
            ) from error

        if result.returncode != 0:
            raise RuntimeError(
                "Xiaohongshu retrieval backend failed with exit code "
                f"{result.returncode}: {result.stderr[-1200:]}"
            )

        logger.info(
            "[PLATFORM DISCOVERY] xiaohongshu retrieval stdout=%s stderr=%s",
            result.stdout[-1200:],
            result.stderr[-1200:],
        )

        notes = parse_mediacrawler_xhs_output(mediacrawler_output_dir)
        payload_text = ""

        if output_path.exists():
            payload_text = output_path.read_text(encoding="utf-8")

        if not payload_text.strip():
            payload_text = result.stdout

        if not notes:
            notes = parse_external_retrieval_payload(payload_text)

        if not notes:
            raise RuntimeError(
                "Xiaohongshu retrieval completed but returned zero real "
                "notes. Check MediaCrawler login/session state and XHS "
                "anti-bot responses."
            )

        normalized = [
            normalize_xiaohongshu_external_note(note)
            for note in notes
            if normalize_external_title(note)
        ][:settings.XIAOHONGSHU_RETRIEVAL_LIMIT]

        logger.info(
            "[PLATFORM DISCOVERY] xiaohongshu normalized %s real notes",
            len(normalized),
        )

        return normalized


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_mediacrawler_path() -> Path:
    media_crawler_path = resolve_repo_root() / "external" / "MediaCrawler"

    if not (media_crawler_path / "main.py").exists():
        raise RuntimeError(
            "MediaCrawler is not installed at external/MediaCrawler. Clone "
            "https://github.com/NanmiCoder/MediaCrawler into external/MediaCrawler "
            "or set XIAOHONGSHU_RETRIEVAL_COMMAND."
        )

    return media_crawler_path


def build_default_mediacrawler_command(
    query: str,
    save_data_path: Path,
    limit: int,
    session_path: Path | None,
) -> list[str]:
    uv_binary = shutil.which("uv")

    if not uv_binary:
        raise RuntimeError(
            "uv is required to run the default MediaCrawler backend. Install "
            "uv or set XIAOHONGSHU_RETRIEVAL_COMMAND to a custom retriever."
        )

    login_args = build_mediacrawler_login_args(session_path)

    return [
        uv_binary,
        "run",
        "python",
        "-c",
        (
            "import config; "
            "config.ENABLE_CDP_MODE=False; "
            "config.CDP_CONNECT_EXISTING=False; "
            "from playwright.async_api import Page; "
            "_geo_goto=Page.goto; "
            "exec(\"async def _geo_safe_goto(self, url, **kwargs):\\n"
            "    kwargs.setdefault('wait_until', 'commit')\\n"
            "    kwargs.setdefault('timeout', 60000)\\n"
            "    try:\\n"
            "        return await _geo_goto(self, url, **kwargs)\\n"
            "    except Exception as error:\\n"
            "        print(f'[GEO XHS] continuing after page.goto failure: {error}')\\n"
            "        return None\\n\"); "
            "Page.goto=_geo_safe_goto; "
            "from main import main, async_cleanup; "
            "from tools.app_runner import run; "
            "run(main, async_cleanup, cleanup_timeout_seconds=15.0)"
        ),
        "--platform",
        "xhs",
        *login_args,
        "--type",
        "search",
        "--keywords",
        query,
        "--get_comment",
        "true",
        "--get_sub_comment",
        "false",
        "--headless",
        "false",
        "--save_data_option",
        "jsonl",
        "--save_data_path",
        str(save_data_path),
        "--crawler_max_notes_count",
        str(max(limit, 20)),
        "--max_comments_count_singlenotes",
        "20",
    ]


def build_mediacrawler_login_args(session_path: Path | None) -> list[str]:
    cookie_string = build_cookie_string_from_storage_state(session_path)

    if cookie_string:
        logger.info(
            "[PLATFORM DISCOVERY] using GEO Xiaohongshu storage_state cookies "
            "for MediaCrawler login."
        )
        return ["--lt", "cookie", "--cookies", cookie_string]

    raise RuntimeError(
        "Canonical Xiaohongshu storage_state.json did not contain "
        "Xiaohongshu/Rednote cookies. Recreate the session at "
        f"{session_path}."
    )


def build_cookie_string_from_storage_state(session_path: Path | None) -> str | None:
    if not session_path or not session_path.exists():
        return None

    try:
        storage_state = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logger.warning(
            "[PLATFORM DISCOVERY] failed to read Xiaohongshu storage_state "
            "%s: %s",
            session_path,
            error,
        )
        return None

    cookies = storage_state.get("cookies") or []
    xhs_cookies = []

    for cookie in cookies:
        domain = str(cookie.get("domain") or "")

        if "xiaohongshu.com" not in domain and "rednote.com" not in domain:
            continue

        name = cookie.get("name")
        value = cookie.get("value")

        if not name or value is None:
            continue

        xhs_cookies.append(f"{name}={value}")

    return "; ".join(xhs_cookies) if xhs_cookies else None


def parse_mediacrawler_xhs_output(save_data_path: Path) -> list[dict]:
    jsonl_dir = save_data_path / "xhs" / "jsonl"

    if not jsonl_dir.exists():
        logger.warning(
            "[PLATFORM DISCOVERY] MediaCrawler XHS output directory missing: %s",
            jsonl_dir,
        )
        return []

    content_files = sorted(jsonl_dir.glob("*_contents_*.jsonl"))
    comment_files = sorted(jsonl_dir.glob("*_comments_*.jsonl"))
    notes = read_jsonl_files(content_files)
    comments = read_jsonl_files(comment_files)

    logger.info(
        "[PLATFORM DISCOVERY] MediaCrawler XHS files contents=%s comments=%s "
        "notes=%s comment_rows=%s",
        [file.name for file in content_files],
        [file.name for file in comment_files],
        len(notes),
        len(comments),
    )

    comments_by_note_id: dict[str, list[dict]] = {}

    for comment in comments:
        note_id = str(comment.get("note_id") or "").strip()

        if not note_id:
            continue

        comments_by_note_id.setdefault(note_id, []).append(comment)

    for note in notes:
        note_id = str(note.get("note_id") or note.get("id") or "").strip()
        note["comments"] = comments_by_note_id.get(note_id, [])

    return notes


def read_jsonl_files(files: list[Path]) -> list[dict]:
    items: list[dict] = []

    for file_path in files:
        for line in file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            if not line:
                continue

            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(
                    "[PLATFORM DISCOVERY] skipping invalid JSONL row in %s",
                    file_path,
                )

    return items


def render_retrieval_command(
    template: str,
    query: str,
    output_path: Path,
    session_path: Path | None,
    limit: int,
    save_data_path: Path,
):
    rendered = template.format(
        query=query,
        output=str(output_path),
        session_path=str(session_path or ""),
        limit=limit,
        save_data_path=str(save_data_path),
    )

    return shlex.split(rendered)


def resolve_xiaohongshu_session_path(account: Account | None = None):
    return SessionResolver().resolve(
        platform="xiaohongshu",
        session_path=account.session_path if account else None,
    )


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
    body = clean_text(
        str(
            first_present(
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
            or ""
        )
    )
    comments = normalize_xiaohongshu_comments(note.get("comments") or [])
    body_with_comments = build_xiaohongshu_body_with_comments(body, comments)
    hashtags = normalize_external_hashtags(note, body_with_comments)
    engagement_metrics = normalize_external_engagement(note)

    raw_metadata = dict(note)
    raw_metadata["normalized_comments"] = comments

    return RetrievedPlatformQuestion(
        platform="xiaohongshu",
        title=title,
        body=body_with_comments or None,
        url=first_present(note, ["url", "note_url", "web_url", "share_url"]),
        author=normalize_external_author(note),
        hashtags=hashtags,
        score=primary_engagement_score(engagement_metrics),
        engagement_metrics=engagement_metrics,
        created_at=parse_datetime(
            first_present(note, ["created_at", "time", "publish_time"])
        ),
        retrieval_method="mediacrawler_xiaohongshu",
        raw_metadata=raw_metadata,
    )


def normalize_xiaohongshu_comments(comments: list[dict]) -> list[dict]:
    normalized_comments = []

    for comment in comments:
        content = clean_text(
            str(
                first_present(
                    comment,
                    ["content", "comment_text", "text", "body"],
                )
                or ""
            )
        )

        if not content:
            continue

        normalized_comments.append(
            {
                "content": content,
                "author": normalize_external_author(comment),
                "score": parse_first_integer(
                    str(
                        first_present(
                            comment,
                            ["like_count", "liked_count", "score"],
                        )
                        or ""
                    )
                ),
                "created_at": first_present(
                    comment,
                    ["create_time", "created_at", "time"],
                ),
            }
        )

    return normalized_comments


def build_xiaohongshu_body_with_comments(
    body: str,
    comments: list[dict],
) -> str:
    sections = []

    if body:
        sections.append(body)

    if comments:
        comment_lines = [
            f"- {comment['content']}"
            for comment in comments[:20]
            if comment.get("content")
        ]

        if comment_lines:
            sections.append("真实评论摘录:\n" + "\n".join(comment_lines))

    return "\n\n".join(sections).strip()


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
    author = (
        note.get("author")
        or note.get("user")
        or note.get("user_info")
        or note.get("nickname")
    )

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
        if isinstance(value, int | float) or str(value).isdigit():
            timestamp = int(value)

            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000

            return datetime.fromtimestamp(timestamp, tz=timezone.utc)

        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except (OSError, OverflowError, ValueError):
        return None
