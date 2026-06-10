from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


def publish_to_reddit(
    username: str,
    password: str,
    subreddit: str,
    title: str,
    body: str,
    dry_run: bool = True,
):

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        context = browser.new_context(
            storage_state="reddit_state.json"
        )

        page = context.new_page()

        page.goto(
            f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT"
        )

        page.wait_for_timeout(10000)

        #
        # Fill title
        #

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

        #
        # Find visible editor
        #

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

        #
        # Fill body
        #

        body_editor.click()

        page.wait_for_timeout(1000)

        body_editor.fill(body)

        page.wait_for_timeout(3000)

        if dry_run:
            print("[DRY RUN] Preparing Reddit submission")

            preview_dir = Path("publishing_previews")

            preview_dir.mkdir(
                exist_ok=True
            )

            preview_timestamp = datetime.now(
                timezone.utc
            )

            screenshot_path = (
                preview_dir /
                f"reddit_preview_{preview_timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            )

            page.screenshot(
                path=str(screenshot_path),
                full_page=True
            )

            print("[DRY RUN] Screenshot saved")
            print("[DRY RUN] Post submission skipped")

            current_url = page.url

            browser.close()

            return {
                "url": current_url,
                "dry_run": True,
                "preview_title": title,
                "preview_subreddit": subreddit,
                "preview_screenshot": str(screenshot_path),
                "preview_timestamp": preview_timestamp.isoformat(),
            }

        #
        # Click Post
        #

        post_button = page.get_by_role(
            "button",
            name="Post"
        )

        post_button.wait_for(
            state="visible",
            timeout=30000
        )

        post_button.click()

        page.wait_for_timeout(10000)

        current_url = page.url

        browser.close()

        return {
            "url": current_url,
            "dry_run": False,
        }
