from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
import sys
import time

from playwright.sync_api import Page, sync_playwright


ACTIVE_REVIEW_SESSIONS = []


@dataclass
class ReviewPublishResult:
    status: str
    url: str
    preview_title: str
    preview_subreddit: str
    preview_url: str
    preview_screenshot: str
    preview_timestamp: str


class ReviewSubmissionAdapter(Protocol):
    platform: str
    display_name: str
    clipboard_origin: str

    def storage_state_paths(self) -> list[Path]:
        ...

    def open_submission_page(self, page: Page, target: str) -> None:
        ...

    def fill_title(self, page: Page, title: str) -> None:
        ...

    def fill_body(self, page: Page, body: str) -> int:
        ...

    def preview_target(self, target: str) -> str:
        ...


def publish_with_review_adapter(
    adapter: ReviewSubmissionAdapter,
    target: str,
    title: str,
    body: str,
) -> dict:
    print(f"[TRACE] entering publish_to_{adapter.platform}")
    print("[TRACE] entering review mode")
    print(
        "[PUBLISH TRACE] playwright_received_title_chars="
        f"{len(title or '')} playwright_received_body_chars={len(body or '')} "
        f"platform={adapter.platform}"
    )

    storage_state_path = resolve_storage_state_path(adapter)
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=False
    )

    context = browser.new_context(
        storage_state=str(storage_state_path)
    )
    context.grant_permissions(
        ["clipboard-read", "clipboard-write"],
        origin=adapter.clipboard_origin,
    )

    page = context.new_page()

    print(f"[REVIEW MODE] Opening {adapter.display_name} submission page")
    adapter.open_submission_page(page, target)

    page.wait_for_timeout(3000)

    print(f"[REVIEW MODE] Filling {adapter.display_name} title")
    adapter.fill_title(page, title)

    page.wait_for_timeout(1000)

    print(f"[REVIEW MODE] Filling {adapter.display_name} body")
    inserted_chars = adapter.fill_body(page, body)

    print(
        "[PUBLISH TRACE] platform_editor_inserted_chars="
        f"{inserted_chars} expected_body_chars={len(body or '')} "
        f"platform={adapter.platform}"
    )

    preview_dir = Path("publishing_previews")
    preview_dir.mkdir(
        exist_ok=True
    )

    preview_timestamp = datetime.now(
        timezone.utc
    )

    screenshot_path = (
        preview_dir /
        (
            f"{adapter.platform}_review_"
            f"{preview_timestamp.strftime('%Y%m%d_%H%M%S')}.png"
        )
    )

    page.screenshot(
        path=str(screenshot_path),
        full_page=True
    )

    preview_url = page.url

    print("[REVIEW MODE] Screenshot captured")
    print("[REVIEW MODE] Submission prepared")
    print("[REVIEW MODE] Waiting for human action")
    print("[REVIEW MODE] Browser intentionally left open")

    ACTIVE_REVIEW_SESSIONS.append({
        "playwright": playwright,
        "browser": browser,
        "context": context,
        "page": page,
        "screenshot_path": str(screenshot_path),
        "platform": adapter.platform,
    })

    wait_for_manual_browser_close(
        browser=browser,
        page=page
    )

    return {
        "status": "review_ready",
        "url": preview_url,
        "preview_title": title,
        "preview_subreddit": adapter.preview_target(target),
        "preview_url": preview_url,
        "preview_screenshot": str(screenshot_path),
        "preview_timestamp": preview_timestamp.isoformat(),
    }


def resolve_storage_state_path(adapter: ReviewSubmissionAdapter) -> Path:
    for path in adapter.storage_state_paths():
        if path.exists():
            return path

    candidate_list = ", ".join(
        str(path)
        for path in adapter.storage_state_paths()
    )
    raise FileNotFoundError(
        f"No saved login state found for {adapter.display_name}. "
        f"Expected one of: {candidate_list}. Generate it before publishing."
    )


def wait_for_manual_browser_close(
    browser,
    page,
):
    print("[TRACE] entering wait_for_manual_browser_close")

    while True:
        try:
            if page.is_closed():
                print("[TRACE] leaving wait_for_manual_browser_close")
                return

            if not browser.is_connected():
                print("[TRACE] leaving wait_for_manual_browser_close")
                return

            open_pages = [
                browser_page
                for context in browser.contexts
                for browser_page in context.pages
                if not browser_page.is_closed()
            ]

            if not open_pages:
                print("[TRACE] leaving wait_for_manual_browser_close")
                return

        except Exception:
            print("[TRACE] leaving wait_for_manual_browser_close")
            return

        time.sleep(2)


def insert_large_body(
    page,
    body_editor,
    body: str,
):
    body = body or ""

    body_editor.click()
    page.wait_for_timeout(1000)
    clear_editor(page)

    try:
        paste_text(
            page=page,
            text=body,
        )
    except Exception as error:
        print(f"[PUBLISH TRACE] clipboard_paste_failed={error}")
        insert_text_in_chunks(
            page=page,
            text=body,
        )

    page.wait_for_timeout(3000)

    inserted_text = get_editor_text(body_editor)

    if len(inserted_text) < len(body):
        print(
            "[PUBLISH TRACE] inserted body shorter than expected; "
            "retrying with chunked keyboard insertion"
        )
        body_editor.click()
        clear_editor(page)
        insert_text_in_chunks(
            page=page,
            text=body,
        )
        page.wait_for_timeout(3000)
        inserted_text = get_editor_text(body_editor)

    if len(inserted_text) < len(body):
        raise RuntimeError(
            "Platform editor insertion failed: inserted "
            f"{len(inserted_text)} of {len(body)} characters"
        )

    return len(inserted_text)


def paste_text(
    page,
    text: str,
):
    page.evaluate(
        """async (value) => {
            await navigator.clipboard.writeText(value);
        }""",
        text,
    )
    page.keyboard.press(paste_shortcut())


def insert_text_in_chunks(
    page,
    text: str,
    chunk_size: int = 4000,
):
    for start in range(0, len(text), chunk_size):
        page.keyboard.insert_text(text[start:start + chunk_size])
        page.wait_for_timeout(150)


def clear_editor(page):
    page.keyboard.press(select_all_shortcut())
    page.keyboard.press("Backspace")


def paste_shortcut():
    return "Meta+V" if sys.platform == "darwin" else "Control+V"


def select_all_shortcut():
    return "Meta+A" if sys.platform == "darwin" else "Control+A"


def get_editor_text(body_editor):
    return body_editor.evaluate(
        """(node) => node.innerText || node.textContent || node.value || "" """
    )


def first_visible_locator(page: Page, selectors: list[str], timeout: int = 30000):
    last_error = None

    for selector in selectors:
        locator = page.locator(selector).first

        try:
            locator.wait_for(
                state="visible",
                timeout=timeout,
            )
            return locator
        except Exception as error:
            last_error = error

    raise RuntimeError(
        "No visible editor matched selectors: "
        f"{', '.join(selectors)}. Last error: {last_error}"
    )


def fill_first_visible(
    page: Page,
    selectors: list[str],
    value: str,
    timeout: int = 30000,
):
    locator = first_visible_locator(
        page=page,
        selectors=selectors,
        timeout=timeout,
    )
    locator.click()
    locator.fill(value)
    return locator


def insert_into_first_visible_editor(
    page: Page,
    selectors: list[str],
    body: str,
    timeout: int = 30000,
):
    editor = first_visible_locator(
        page=page,
        selectors=selectors,
        timeout=timeout,
    )
    return insert_large_body(
        page=page,
        body_editor=editor,
        body=body,
    )
