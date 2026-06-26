from datetime import datetime, timezone
from pathlib import Path
import sys
import time

from playwright.sync_api import sync_playwright


ACTIVE_REVIEW_SESSIONS = []


def publish_to_reddit(
    username: str,
    password: str,
    subreddit: str,
    title: str,
    body: str,
):
    print("[TRACE] entering publish_to_reddit")
    print("[TRACE] entering review mode")
    print(
        "[PUBLISH TRACE] playwright_received_title_chars="
        f"{len(title or '')} playwright_received_body_chars={len(body or '')}"
    )

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=False
    )

    context = browser.new_context(
        storage_state="reddit_state.json"
    )
    context.grant_permissions(
        ["clipboard-read", "clipboard-write"],
        origin="https://www.reddit.com",
    )

    page = context.new_page()

    print("[REVIEW MODE] Opening Reddit submission page")

    page.goto(
        f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT"
    )

    page.wait_for_timeout(10000)

    print("[REVIEW MODE] Filling title")

    title_box = page.locator(
        'textarea[name="title"]'
    ).first

    title_box.wait_for(
        state="visible",
        timeout=30000
    )

    title_box.click()

    title_box.fill(title)

    page.wait_for_timeout(2000)

    editors = page.locator(
        '[contenteditable="true"]'
    )

    count = editors.count()

    body_editor = None

    for i in range(count):

        editor = editors.nth(i)

        if editor.is_visible():

            body_editor = editor

            break

    if body_editor is None:

        raise Exception(
            "No visible editor found"
        )

    print("[REVIEW MODE] Filling body")

    inserted_chars = insert_large_body(
        page=page,
        body_editor=body_editor,
        body=body,
    )

    print(
        "[PUBLISH TRACE] reddit_editor_inserted_chars="
        f"{inserted_chars} expected_body_chars={len(body or '')}"
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
        f"reddit_review_{preview_timestamp.strftime('%Y%m%d_%H%M%S')}.png"
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
    })

    wait_for_manual_browser_close(
        browser=browser,
        page=page
    )

    return {
        "status": "review_ready",
        "url": preview_url,
        "preview_title": title,
        "preview_subreddit": subreddit,
        "preview_url": preview_url,
        "preview_screenshot": str(screenshot_path),
        "preview_timestamp": preview_timestamp.isoformat(),
    }


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
            "Reddit editor insertion failed: inserted "
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
        """(node) => node.innerText || node.textContent || "" """
    )
