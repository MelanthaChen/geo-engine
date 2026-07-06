import json
import logging
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile

from app.core.config import settings
from app.models.account import Account
from app.services.platform_retrievers.base import (
    RetrievedPlatformQuestion,
    RetrievalError,
)
from app.services.platform_retrievers.utils import (
    clean_text,
    first_present,
    parse_datetime,
    parse_first_integer,
)
from app.services.session_resolver import SessionResolver


logger = logging.getLogger(__name__)


class XiaohongshuRetriever:
    platform = "xiaohongshu"

    def search(
        self,
        query: str,
        limit: int,
        *,
        account: Account | None = None,
        **_,
    ) -> list[RetrievedPlatformQuestion]:
        command_template = settings.XIAOHONGSHU_RETRIEVAL_COMMAND

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_path = temp_path / "xiaohongshu_results.jsonl"
            save_data_path = temp_path / "mediacrawler_output"
            session_path = resolve_xiaohongshu_session_path(account=account)

            if command_template:
                command = render_retrieval_command(
                    template=command_template,
                    query=query,
                    output_path=output_path,
                    session_path=session_path,
                    limit=limit,
                    save_data_path=save_data_path,
                )
                cwd = None
                backend_name = "configured command"
            else:
                command = build_default_mediacrawler_command(
                    query=query,
                    save_data_path=save_data_path,
                    limit=limit,
                    session_path=session_path,
                )
                cwd = resolve_mediacrawler_path()
                backend_name = "MediaCrawler"

            logger.info(
                "[RETRIEVAL] running Xiaohongshu backend=%s query=%r limit=%s",
                backend_name,
                query,
                limit,
            )

            result = run_retrieval_command(command=command, cwd=cwd)
            notes = parse_mediacrawler_xhs_output(save_data_path)

            if not notes:
                payload_text = ""

                if output_path.exists():
                    payload_text = output_path.read_text(encoding="utf-8")

                if not payload_text.strip():
                    payload_text = result.stdout

                notes = parse_external_retrieval_payload(payload_text)

            if not notes:
                raise RetrievalError(
                    "Xiaohongshu retrieval completed but returned zero real "
                    "notes. Check MediaCrawler login/session state and XHS "
                    "anti-bot responses."
                )

            normalized = [
                normalize_xiaohongshu_note(note)
                for note in notes
                if normalize_external_title(note)
            ][:limit]

            if not normalized:
                raise RetrievalError(
                    "Xiaohongshu retrieval returned rows, but no rows had "
                    "a usable title after normalization."
                )

            logger.info(
                "[RETRIEVAL] Xiaohongshu normalized %s real notes",
                len(normalized),
            )
            return normalized

    def fetch_post(
        self,
        url: str,
        *,
        account: Account | None = None,
    ) -> RetrievedPlatformQuestion:
        raise RetrievalError(
            "Xiaohongshu fetch_post is delegated to MediaCrawler search output "
            "for now; direct note fetch is not exposed separately."
        )

    def fetch_comments(
        self,
        url: str,
        *,
        account: Account | None = None,
    ) -> list[dict]:
        raise RetrievalError(
            "Xiaohongshu fetch_comments is delegated to MediaCrawler search "
            "with comment collection for now."
        )


def run_retrieval_command(command: list[str], cwd: Path | None):
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
        stdout = (
            error.stdout.decode("utf-8", "replace")
            if isinstance(error.stdout, bytes)
            else (error.stdout or "")
        )
        stderr = (
            error.stderr.decode("utf-8", "replace")
            if isinstance(error.stderr, bytes)
            else (error.stderr or "")
        )
        raise RetrievalError(
            "Xiaohongshu retrieval timed out before returning real notes. "
            "This usually means MediaCrawler is waiting for a valid "
            "Xiaohongshu login/session or is blocked before search. "
            f"stdout={stdout[-800:]} stderr={stderr[-800:]}"
        ) from error

    if result.returncode != 0:
        raise RetrievalError(
            "Xiaohongshu retrieval backend failed with exit code "
            f"{result.returncode}: {result.stderr[-1200:]}"
        )

    logger.info(
        "[RETRIEVAL] Xiaohongshu stdout=%s stderr=%s",
        result.stdout[-1200:],
        result.stderr[-1200:],
    )
    return result


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_mediacrawler_path() -> Path:
    media_crawler_path = resolve_repo_root() / "external" / "MediaCrawler"

    if not (media_crawler_path / "main.py").exists():
        raise RetrievalError(
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
        raise RetrievalError(
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
            "[RETRIEVAL] using GEO Xiaohongshu storage_state cookies "
            "for MediaCrawler login."
        )
        return ["--lt", "cookie", "--cookies", cookie_string]

    raise RetrievalError(
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
            "[RETRIEVAL] failed to read Xiaohongshu storage_state %s: %s",
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
            "[RETRIEVAL] MediaCrawler XHS output directory missing: %s",
            jsonl_dir,
        )
        return []

    content_files = sorted(jsonl_dir.glob("*_contents_*.jsonl"))
    comment_files = sorted(jsonl_dir.glob("*_comments_*.jsonl"))
    notes = read_jsonl_files(content_files)
    comments = read_jsonl_files(comment_files)

    logger.info(
        "[RETRIEVAL] MediaCrawler XHS files contents=%s comments=%s "
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
                    "[RETRIEVAL] skipping invalid JSONL row in %s",
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
                    "[RETRIEVAL] skipping non-JSON retrieval line: %s",
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


def normalize_xiaohongshu_note(note: dict):
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
        hashtags = [normalize_hashtag_item(item) for item in raw_hashtags]
    else:
        hashtags = []

    hashtags.extend(re.findall(r"#[^\s#]+", body or ""))

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
