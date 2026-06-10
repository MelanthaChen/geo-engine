from datetime import datetime, timezone
from pathlib import Path
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
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=False
    )

    context = browser.new_context(
        storage_state="reddit_state.json"
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

    body_editor.click()

    page.wait_for_timeout(1000)

    body_editor.fill(body)

    page.wait_for_timeout(3000)

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
    while True:
        try:
            if page.is_closed():
                return

            if not browser.is_connected():
                return

            open_pages = [
                browser_page
                for context in browser.contexts
                for browser_page in context.pages
                if not browser_page.is_closed()
            ]

            if not open_pages:
                return

        except Exception:
            return

        time.sleep(2)
