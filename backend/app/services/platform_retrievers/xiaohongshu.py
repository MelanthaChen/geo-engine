import json
import logging
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
from urllib.parse import quote_plus

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
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


SEARCH_URL = "https://www.rednote.com/search_result?keyword={query}"
SEARCH_RESULT_WAIT_MS = 20_000
NOTE_PAGE_WAIT_MS = 10_000
SCROLL_PAUSE_MS = 1200
MAX_SEARCH_SCROLLS = 10
MAX_COMMENTS_PER_NOTE = 30
MIN_EXPECTED_NOTE_ITEMS = 20

SEARCH_RESULT_SELECTORS = [
    'a[href*="/explore/"]',
    'a[href*="/discovery/item/"]',
    ".note-item",
    "section.note-item",
]

NOTE_CONTENT_SELECTORS = [
    "#detail-title",
    "#detail-desc",
    ".note-content",
    ".note-detail-mask",
    ".interaction-container",
    'meta[property="og:title"]',
]


def log_platform_faq_debug(event: str, **fields):
    logger.info(
        "[PLATFORM FAQ DEBUG] %s",
        json.dumps({"event": event, **fields}, default=str),
    )


class BrowserSearchRetriever:
    platform = "xiaohongshu"

    def search(
        self,
        query: str,
        limit: int,
        *,
        account: Account | None = None,
        **_,
    ) -> list[RetrievedPlatformQuestion]:
        session_path = resolve_xiaohongshu_session_path(account=account)
        log_platform_faq_debug(
            "xiaohongshu_retriever.search.received",
            backend="browser_search",
            query=query,
            limit=limit,
            account_id=getattr(account, "id", None),
            account_handle=getattr(account, "handle", None),
            account_session_path=getattr(account, "session_path", None),
            session_path=str(session_path),
        )

        notes = run_browser_search(
            query=query,
            limit=limit,
            session_path=session_path,
        )

        if not notes:
            raise RetrievalError(
                "Browser-based Xiaohongshu retrieval returned zero real notes. "
                "Check the web login session, Xiaohongshu page structure, and "
                "whether the search results page is showing risk-control UI."
            )

        normalized = [
            normalize_xiaohongshu_note(note)
            for note in notes
            if normalize_external_title(note)
        ][:limit]
        log_platform_faq_debug(
            "xiaohongshu_retriever.normalized",
            backend="browser_search",
            raw_notes_count=len(notes),
            normalized_question_count=len(normalized),
            selectors={
                "search_results": SEARCH_RESULT_SELECTORS,
                "note_content": NOTE_CONTENT_SELECTORS,
            },
        )

        if not normalized:
            raise RetrievalError(
                "Browser-based Xiaohongshu retrieval found pages, but no rows "
                "had a usable title after normalization."
            )

        logger.info(
            "[RETRIEVAL] Xiaohongshu browser search normalized %s real notes",
            len(normalized),
        )
        return normalized

    def fetch_post(
        self,
        url: str,
        *,
        account: Account | None = None,
    ) -> RetrievedPlatformQuestion:
        session_path = resolve_xiaohongshu_session_path(account=account)
        note = run_browser_note_fetch(
            url=url,
            session_path=session_path,
        )
        return normalize_xiaohongshu_note(note)

    def fetch_comments(
        self,
        url: str,
        *,
        account: Account | None = None,
    ) -> list[dict]:
        session_path = resolve_xiaohongshu_session_path(account=account)
        note = run_browser_note_fetch(
            url=url,
            session_path=session_path,
        )
        return normalize_xiaohongshu_comments(note.get("comments") or [])


class XiaohongshuRetriever(BrowserSearchRetriever):
    """Active Xiaohongshu retriever using browser search."""


def run_browser_search(
    query: str,
    limit: int,
    session_path: Path,
) -> list[dict]:
    search_url = SEARCH_URL.format(query=quote_plus(query))

    logger.info(
        "[RETRIEVAL] Xiaohongshu browser search query=%r limit=%s url=%s",
        query,
        limit,
        search_url,
    )
    log_platform_faq_debug(
        "xiaohongshu_retriever.browser_search.start",
        query=query,
        limit=limit,
        search_url=search_url,
        session_path=str(session_path),
    )

    with sync_playwright() as playwright:
        context, browser = launch_xiaohongshu_browser_context(
            playwright=playwright,
            purpose="web",
            session_path=session_path,
        )
        page = context.new_page()

        try:
            goto_xiaohongshu_page(page, search_url)
            submit_search_form_if_needed(page, query)
            wait_for_search_results(page)
            wait_for_note_item_count(
                page=page,
                minimum=MIN_EXPECTED_NOTE_ITEMS,
            )
            search_items = collect_search_results(
                page=page,
                limit=limit,
            )

            notes = []
            for item in search_items[:limit]:
                try:
                    note = fetch_note_from_page(
                        context=context,
                        search_item=item,
                    )
                    notes.append(note)
                except Exception as error:
                    logger.warning(
                        "[RETRIEVAL] failed to fetch Xiaohongshu note %s: %s",
                        item.get("url"),
                        error,
                    )
                    fallback_note = dict(item)
                    fallback_note["comments"] = []
                    fallback_note["retrieval_error"] = str(error)
                    notes.append(fallback_note)

            log_platform_faq_debug(
                "xiaohongshu_retriever.browser_search.completed",
                search_items_count=len(search_items),
                notes_count=len(notes),
                note_urls=[note.get("url") for note in notes],
            )
            return notes
        finally:
            context.close()
            if browser:
                browser.close()


def run_browser_note_fetch(
    url: str,
    session_path: Path,
) -> dict:
    with sync_playwright() as playwright:
        context, browser = launch_xiaohongshu_browser_context(
            playwright=playwright,
            purpose="web",
            session_path=session_path,
        )
        try:
            return fetch_note_from_page(
                context=context,
                search_item={"url": url},
            )
        finally:
            context.close()
            if browser:
                browser.close()


def launch_xiaohongshu_browser_context(
    playwright,
    purpose: str,
    session_path: Path | None = None,
):
    resolver = SessionResolver()
    profile_dir = resolver.canonical_profile_dir(
        platform="xiaohongshu",
        purpose=purpose,
    )

    if profile_dir.exists():
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=False,
            locale="zh-CN",
            viewport={"width": 1440, "height": 1100},
        )
        return context, None

    storage_state_path = session_path

    if storage_state_path and storage_state_path.is_dir():
        storage_state_path = None

    if not storage_state_path:
        storage_state_path = resolver.resolve_storage_state(
            platform="xiaohongshu",
            purpose=purpose,
        )

    browser = playwright.chromium.launch(
        channel="chrome",
        headless=False,
    )
    context = browser.new_context(
        storage_state=str(storage_state_path),
        locale="zh-CN",
        viewport={"width": 1440, "height": 1100},
    )
    return context, browser


def wait_for_search_results(page):
    for selector in SEARCH_RESULT_SELECTORS:
        try:
            page.wait_for_selector(selector, timeout=SEARCH_RESULT_WAIT_MS)
            log_platform_faq_debug(
                "xiaohongshu_retriever.browser_search.selector_ready",
                selector=selector,
            )
            return
        except PlaywrightTimeoutError:
            continue

    page_text = extract_page_text_snippet(page)
    login_hint = "登录探索更多内容" in page_text or "登录" in page_text[:200]
    log_platform_faq_debug(
        "xiaohongshu_retriever.browser_search.no_results",
        current_url=page.url,
        selectors=SEARCH_RESULT_SELECTORS,
        login_hint=login_hint,
        page_text_first_1000=page_text[:1000],
    )
    raise RetrievalError(
        "Xiaohongshu search page loaded, but no result selector appeared. "
        f"Tried selectors: {SEARCH_RESULT_SELECTORS}. "
        f"Current URL: {page.url}. "
        f"Login hint: {login_hint}. "
        f"Page text: {page_text[:500]}"
    )


def wait_for_note_item_count(page, minimum: int):
    try:
        page.wait_for_function(
            """
            (minimum) => document.querySelectorAll('.note-item').length >= minimum
            """,
            arg=minimum,
            timeout=SEARCH_RESULT_WAIT_MS,
        )
        log_platform_faq_debug(
            "xiaohongshu_retriever.browser_search.note_items_ready",
            minimum=minimum,
            note_item_count=page.locator(".note-item").count(),
        )
    except PlaywrightTimeoutError:
        note_item_count = page.locator(".note-item").count()
        log_platform_faq_debug(
            "xiaohongshu_retriever.browser_search.note_items_timeout",
            minimum=minimum,
            note_item_count=note_item_count,
            current_url=page.url,
            page_text_first_500=extract_page_text_snippet(page)[:500],
        )

        if note_item_count == 0:
            raise RetrievalError(
                "Xiaohongshu search page did not expose any .note-item cards "
                f"before timeout. Current URL: {page.url}."
            )


def extract_page_text_snippet(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=3000)
    except Exception:
        return ""


def submit_search_form_if_needed(page, query: str):
    if extract_search_results(page):
        return

    input_locator = page.locator(
        'input.search-input, input[placeholder*="搜索"], input[type="text"]'
    ).first

    try:
        if input_locator.count() == 0:
            return

        input_locator.click(timeout=5000)
        input_locator.fill(query, timeout=5000)
        input_locator.press("Enter", timeout=5000)
        page.wait_for_timeout(2500)

        if extract_search_results(page):
            return

        button_locator = page.locator(
            'button:has-text("搜索"), button.min-width-search-icon, button[type="submit"]'
        ).first

        if button_locator.count() > 0:
            button_locator.click(timeout=5000)
            page.wait_for_timeout(2500)
    except PlaywrightTimeoutError:
        logger.warning(
            "[RETRIEVAL] Xiaohongshu search input submission timed out; "
            "continuing with selector wait. url=%s",
            page.url,
        )


def collect_search_results(page, limit: int) -> list[dict]:
    previous_count = -1
    stable_scrolls = 0

    for scroll_index in range(MAX_SEARCH_SCROLLS + 1):
        results = extract_search_results(page)
        log_platform_faq_debug(
            "xiaohongshu_retriever.browser_search.scroll",
            scroll_index=scroll_index,
            parsed_results=len(results),
            current_url=page.url,
        )

        if len(results) >= limit:
            return results[:limit]

        if len(results) == previous_count:
            stable_scrolls += 1
        else:
            stable_scrolls = 0
            previous_count = len(results)

        if stable_scrolls >= 3:
            return results[:limit]

        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(SCROLL_PAUSE_MS)

    return extract_search_results(page)[:limit]


def extract_search_results(page) -> list[dict]:
    return page.evaluate(
        """
        () => {
          const normalizeText = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const absoluteUrl = (href) => {
            if (!href) return null;
            try { return new URL(href, window.location.origin).toString(); }
            catch (_) { return href; }
          };
          const firstText = (root, selectors) => {
            for (const selector of selectors) {
              const element = root.querySelector(selector);
              const text = normalizeText(element?.innerText || element?.textContent || '');
              if (text) return text;
            }
            return '';
          };
          const isVisible = (element) => {
            if (!element) return false;
            const rect = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return rect.width > 0 && rect.height > 0 &&
              style.display !== 'none' && style.visibility !== 'hidden';
          };
          const parseCount = (value) => {
            const text = normalizeText(value);
            if (!text) return null;
            const lower = text.toLowerCase();
            const match = lower.match(/[\\d,.]+/);
            if (!match) return null;
            const number = Number(match[0].replace(/,/g, ''));
            if (Number.isNaN(number)) return null;
            if (/[万w]/i.test(lower)) return Math.round(number * 10000);
            if (/k/i.test(lower)) return Math.round(number * 1000);
            return Math.round(number);
          };
          const noteCards = Array.from(document.querySelectorAll('.note-item, section.note-item'));
          const seen = new Set();
          const items = [];

          for (const card of noteCards) {
            const anchors = Array.from(
              card.querySelectorAll(
                'a[href*="/search_result/"], a[href*="/explore/"], ' +
                'a[href*="/discovery/item/"], a[href*="/note/"]'
              )
            );
            const anchor =
              anchors.find((candidate) =>
                isVisible(candidate) && candidate.href.includes('xsec_token=')
              ) ||
              anchors.find((candidate) =>
                isVisible(candidate) && !candidate.href.includes('/user/profile/')
              ) ||
              anchors.find((candidate) => !candidate.href.includes('/user/profile/'));
            if (!anchor) continue;
            const url = absoluteUrl(anchor.getAttribute('href'));
            if (!url || seen.has(url) || !/(search_result|explore|discovery|note|item)/i.test(url)) continue;
            seen.add(url);

            const title = firstText(card, [
              '.title',
              '.note-title',
              '.note-title span',
              '.footer .title',
              '[class*="title"]',
              'a[title]'
            ]) || normalizeText(anchor.innerText || anchor.textContent || '');
            const author = firstText(card, [
              '.author .name',
              '.author-wrapper .name',
              '.name-time-wrapper .name',
              '.author',
              '.author-wrapper',
              '.name',
              '.nickname',
              '[class*="author"]',
              '[class*="name"]',
              '[class*="nick"]'
            ]);
            const likes = firstText(card, [
              '.like-wrapper',
              '.count',
              '.likes',
              '[class*="like"]',
              '[class*="count"]'
            ]);
            const publishTime = firstText(card, [
              'time',
              '.author .time',
              '.author-wrapper [class*="time"]',
              '.name-time-wrapper [class*="time"]',
              '.date',
              '[class*="date"]',
              '[class*="time"]'
            ]);

            if (!title && !normalizeText(card.innerText || card.textContent || '')) continue;

            items.push({
              title,
              url,
              author,
              likes,
              liked_count: parseCount(likes),
              publish_time: publishTime,
              search_card_text: normalizeText(card.innerText || card.textContent || '')
            });
          }

          return items;
        }
        """
    )


def fetch_note_from_page(context, search_item: dict) -> dict:
    url = search_item.get("url")

    if not url:
        raise RetrievalError("Cannot fetch Xiaohongshu note without a URL.")

    page = context.new_page()

    try:
        goto_xiaohongshu_page(page, url)
        wait_for_note_content(page)
        scroll_note_comments(page)
        note = extract_note_detail(page)
        note.update({key: value for key, value in search_item.items() if value})
        note["url"] = page.url or url
        note["retrieval_method"] = "browser_xiaohongshu"
        return note
    finally:
        page.close()


def goto_xiaohongshu_page(page, url: str):
    try:
        page.goto(
            url,
            wait_until="commit",
            timeout=NOTE_PAGE_WAIT_MS,
        )
    except PlaywrightTimeoutError:
        logger.warning(
            "[RETRIEVAL] Xiaohongshu navigation timed out after commit wait; "
            "continuing with DOM polling. url=%s current_url=%s",
            url,
            page.url,
        )


def wait_for_note_content(page):
    try:
        page.wait_for_selector(
            ", ".join(NOTE_CONTENT_SELECTORS),
            timeout=NOTE_PAGE_WAIT_MS,
        )
        return
    except PlaywrightTimeoutError:
        pass

    logger.warning(
        "[RETRIEVAL] Xiaohongshu note content selectors did not appear. "
        "Continuing with DOM fallback. url=%s selectors=%s",
        page.url,
        NOTE_CONTENT_SELECTORS,
    )


def scroll_note_comments(page):
    for _ in range(8):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(800)


def extract_note_detail(page) -> dict:
    return page.evaluate(
        f"""
        () => {{
          const normalizeText = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const firstTextFromRoot = (root, selectors) => {{
            for (const selector of selectors) {{
              const element = root.querySelector(selector);
              const text = normalizeText(element?.innerText || element?.textContent || '');
              if (text) return text;
            }}
            return '';
          }};
          const firstText = (selectors) => {{
            for (const selector of selectors) {{
              const element = document.querySelector(selector);
              const text = normalizeText(element?.innerText || element?.textContent || element?.getAttribute?.('content') || '');
              if (text) return text;
            }}
            return '';
          }};
          const extractHashtags = (text) => {{
            const tags = new Set();
            for (const match of (text || '').matchAll(/#[^\\s#]+/g)) {{
              tags.add(match[0]);
            }}
            document.querySelectorAll('a[href*="search_result"], a[href*="hashtag"], span').forEach((element) => {{
              const value = normalizeText(element.innerText || element.textContent || '');
              if (value.startsWith('#')) tags.add(value);
            }});
            return Array.from(tags);
          }};
          const parseComments = () => {{
            const selectors = [
              '.comment-item',
              '[class*="comment-item"]',
              '[class*="commentItem"]',
              '.parent-comment',
              '[class*="parent-comment"]',
              '[class*="comment"]'
            ];
            const nodes = [];
            for (const selector of selectors) {{
              document.querySelectorAll(selector).forEach((node) => nodes.push(node));
              if (nodes.length) break;
            }}
            const seen = new Set();
            return nodes.map((node) => {{
              const content = firstTextFromRoot(node, [
                '.content',
                '.comment-content',
                '.comment-inner-content',
                '[class*="content"]',
                '[class*="text"]',
                'span'
              ]) || normalizeText(node.innerText || node.textContent || '');
              const author = firstTextFromRoot(node, [
                '.author',
                '.name',
                '.nickname',
                '[class*="author"]',
                '[class*="name"]',
                '[class*="nick"]'
              ]);
              const score = firstTextFromRoot(node, [
                '.like',
                '.count',
                '.like-count',
                '[class*="like"]',
                '[class*="count"]'
              ]);
              const key = `${{author}}|${{content}}`;
              if (!content || seen.has(key)) return null;
              seen.add(key);
              return {{ content, author, score }};
            }}).filter(Boolean).slice(0, {MAX_COMMENTS_PER_NOTE});
          }};

          const title = firstText([
            '#detail-title',
            '.title',
            '.note-title',
            '[class*="title"]',
            'meta[property="og:title"]'
          ]);
          const body = firstText([
            '#detail-desc',
            '.desc',
            '.note-text',
            '.note-content',
            '[class*="desc"]',
            '[class*="content"]'
          ]);
          const pageText = normalizeText(document.body?.innerText || '');
          const author = firstText([
            '.author .name',
            '.user .name',
            '.nickname',
            '[class*="author"] [class*="name"]',
            '[class*="nickname"]'
          ]);
          const likes = firstText([
            '.like-wrapper',
            '.like',
            '.like-count',
            '[class*="like"]',
            '[class*="interact"]'
          ]);
          const publishTime = firstText([
            'time',
            '.date',
            '[class*="date"]',
            '[class*="time"]'
          ]);
          const comments = parseComments();

          return {{
            title,
            body: body || pageText,
            author,
            likes,
            publish_time: publishTime,
            hashtags: extractHashtags(`${{title}} ${{body || pageText}}`),
            comments,
            raw_page_text_length: pageText.length
          }};
        }}
        """
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

    log_platform_faq_debug(
        "xiaohongshu_retriever.subprocess.completed",
        returncode=result.returncode,
        stdout_first_1000=(result.stdout or "")[:1000],
        stderr_first_1000=(result.stderr or "")[:1000],
    )

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
        log_platform_faq_debug(
            "xiaohongshu_retriever.jsonl.missing",
            jsonl_dir=str(jsonl_dir),
            jsonl_generated=False,
        )
        return []

    content_files = sorted(jsonl_dir.glob("*_contents_*.jsonl"))
    comment_files = sorted(jsonl_dir.glob("*_comments_*.jsonl"))
    notes = read_jsonl_files(content_files)
    comments = read_jsonl_files(comment_files)
    log_platform_faq_debug(
        "xiaohongshu_retriever.jsonl.generated",
        jsonl_dir=str(jsonl_dir),
        jsonl_generated=bool(content_files or comment_files),
        content_file_paths=[str(file) for file in content_files],
        comment_file_paths=[str(file) for file in comment_files],
        parsed_notes_count=len(notes),
        parsed_comments_count=len(comments),
    )

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
    resolver = SessionResolver()

    try:
        return resolver.resolve_profile(
            platform="xiaohongshu",
            purpose="web",
        )
    except FileNotFoundError:
        try:
            return resolver.resolve_storage_state(
                platform="xiaohongshu",
                purpose="web",
            )
        except FileNotFoundError as error:
            profile_dir = resolver.canonical_profile_dir(
                platform="xiaohongshu",
                purpose="web",
            )
            storage_path = resolver.canonical_storage_state_path(
                platform="xiaohongshu",
                purpose="web",
            )
            raise FileNotFoundError(
                "No Xiaohongshu web browser session found. Create the "
                "persistent profile with: "
                "python save_platform_state.py xiaohongshu --purpose web. "
                f"Expected profile: {profile_dir}. Legacy fallback: "
                f"{storage_path}."
            ) from error


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
        retrieval_method=note.get("retrieval_method") or "mediacrawler_xiaohongshu",
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
