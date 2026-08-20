from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
import sys
import time

from playwright.sync_api import Page, sync_playwright


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

    def wait_until_ready(self, page: Page) -> None:
        ...

    def fill_title(self, page: Page, title: str) -> None:
        ...

    def fill_body(self, page: Page, body: str) -> int:
        ...

    def preview_target(self, target: str) -> str:
        ...


def review_completion_instructions() -> str:
    return """
---------------------------------------
Review is ready.

You may:

• Edit title/body manually
• Upload/remove images
• Click Publish manually if desired

When you are finished reviewing,
return to this terminal and press ENTER.

Press Ctrl+C to abort.
---------------------------------------
"""


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

    playwright = sync_playwright().start()
    context = None
    page = None

    try:
        context, _browser = launch_review_context(
            playwright=playwright,
            adapter=adapter,
        )

        context.grant_permissions(
            ["clipboard-read", "clipboard-write"],
            origin=adapter.clipboard_origin,
        )

        page = context.new_page()

        print(f"[REVIEW MODE] Opening {adapter.display_name} submission page")
        adapter.open_submission_page(page, target)

        wait_until_ready = getattr(adapter, "wait_until_ready", None)

        if wait_until_ready:
            wait_until_ready(page)
        else:
            page.wait_for_load_state("domcontentloaded")

        print(f"[REVIEW MODE] Filling {adapter.display_name} title")
        title_inserted_chars = adapter.fill_title(page, title)
        print(
            "[PUBLISH TRACE] platform_title_inserted_chars="
            f"{title_inserted_chars} expected_title_chars={len(title or '')} "
            f"platform={adapter.platform}"
        )

        print(f"[REVIEW MODE] Filling {adapter.display_name} body")
        inserted_chars = adapter.fill_body(page, body)

        print(
            "[PUBLISH TRACE] platform_editor_inserted_chars="
            f"{inserted_chars} expected_body_chars={len(body or '')} "
            f"platform={adapter.platform}"
        )

        wait_until_review_ready = getattr(adapter, "wait_until_review_ready", None)
        publish_enabled = None

        if wait_until_review_ready:
            publish_enabled = wait_until_review_ready(page)

        preview_dir = Path("publishing_previews")
        preview_dir.mkdir(
            exist_ok=True
        )

        preview_timestamp = datetime.now(
            timezone.utc
        )

        screenshot_path_factory = getattr(adapter, "review_screenshot_path", None)

        if screenshot_path_factory:
            screenshot_path = screenshot_path_factory()
        else:
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
        page_title = page.title()
        creator_nickname = extract_creator_nickname(page)

        print("[REVIEW MODE] Screenshot captured")
        print("[REVIEW MODE] Submission prepared")
        print(f"[REVIEW MODE] creator_profile_path={current_profile_path(adapter)}")
        print(f"[REVIEW MODE] current_url={preview_url}")
        print(f"[REVIEW MODE] page_title={page_title}")
        print(f"[REVIEW MODE] creator_nickname={creator_nickname or 'unknown'}")
        print(f"[REVIEW MODE] title_inserted_length={title_inserted_chars}")
        print(f"[REVIEW MODE] body_inserted_length={inserted_chars}")
        if publish_enabled is not None:
            print(f"[REVIEW MODE] publish_enabled={publish_enabled}")
        print("[REVIEW MODE] browser_remained_open=true")
        print("READY_FOR_REVIEW")

        review_completion = wait_for_terminal_review_completion(
            page=page,
            context=context,
            adapter=adapter,
            preview_dir=preview_dir,
        )

        print("[REVIEW MODE] Review completed by terminal confirmation")
        print(f"[REVIEW MODE] final_current_url={review_completion['current_url']}")
        print(f"[REVIEW MODE] final_page_title={review_completion['page_title']}")
        print(f"[REVIEW MODE] final_publish_enabled={review_completion['publish_enabled']}")
        print(f"[REVIEW MODE] final_screenshot={review_completion['screenshot_path']}")

        return {
            "status": "review_ready",
            "url": preview_url,
            "preview_title": title,
            "preview_subreddit": adapter.preview_target(target),
            "preview_url": preview_url,
            "preview_screenshot": str(screenshot_path),
            "preview_timestamp": preview_timestamp.isoformat(),
        }
    except KeyboardInterrupt:
        print("[REVIEW MODE] Review aborted by Ctrl+C")
        raise
    finally:
        close_review_page_context(
            page=page,
            context=context,
        )
        playwright.stop()


def wait_for_terminal_review_completion(
    page: Page,
    context,
    adapter: ReviewSubmissionAdapter,
    preview_dir: Path,
) -> dict:
    print(review_completion_instructions())
    input("Press ENTER after review is complete...")

    completion = capture_review_completion_state(
        page=page,
        adapter=adapter,
        preview_dir=preview_dir,
    )

    return completion


def capture_review_completion_state(
    page: Page,
    adapter: ReviewSubmissionAdapter,
    preview_dir: Path,
) -> dict:
    screenshot_path = preview_dir / "review_finished.png"

    if page is None or page.is_closed():
        return {
            "current_url": "page_closed",
            "page_title": "page_closed",
            "publish_enabled": None,
            "screenshot_path": "",
        }

    current_url = page.url
    page_title = page.title()
    publish_enabled = detect_publish_enabled(
        page=page,
        adapter=adapter,
    )

    page.screenshot(
        path=str(screenshot_path),
        full_page=True,
    )

    return {
        "current_url": current_url,
        "page_title": page_title,
        "publish_enabled": publish_enabled,
        "screenshot_path": str(screenshot_path),
    }


def detect_publish_enabled(
    page: Page,
    adapter: ReviewSubmissionAdapter,
) -> bool | None:
    detector = getattr(adapter, "detect_publish_enabled", None)

    if detector:
        return detector(page)

    try:
        return page.evaluate(
            """() => {
                const xhsButton = document.querySelector('xhs-publish-btn[submit-text*="发布"]');
                if (xhsButton) {
                    return xhsButton.getAttribute('submit-disabled') !== 'true' &&
                        xhsButton.getAttribute('aria-disabled') !== 'true' &&
                        !xhsButton.hasAttribute('disabled');
                }

                const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
                const publishButton = buttons.find((element) =>
                    (element.innerText || element.textContent || '').includes('发布')
                );

                if (!publishButton) {
                    return null;
                }

                return publishButton.getAttribute('aria-disabled') !== 'true' &&
                    !publishButton.hasAttribute('disabled');
            }"""
        )
    except Exception:
        return None


def close_review_page_context(
    page: Page | None,
    context,
) -> None:
    try:
        if page and not page.is_closed():
            page.close()
            print("[REVIEW MODE] Playwright page closed.")
    except Exception as error:
        print(f"[REVIEW MODE] page close skipped: {error}")

    try:
        if context:
            context.close()
            print("[REVIEW MODE] Playwright context closed.")
    except Exception as error:
        print(f"[REVIEW MODE] context close skipped: {error}")


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


def resolve_profile_dir(adapter: ReviewSubmissionAdapter) -> Path | None:
    profile_dir_paths = getattr(adapter, "profile_dir_paths", None)

    if not profile_dir_paths:
        return None

    for path in profile_dir_paths():
        if path.exists():
            return path

    return None


def launch_review_context(playwright, adapter: ReviewSubmissionAdapter):
    profile_dir = resolve_profile_dir(adapter)

    if profile_dir:
        print("Launching creator profile...")
        print(f"[REVIEW MODE] creator_profile_path={profile_dir}")
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=False,
        )
        print("Creator profile loaded.")
        return context, context.browser

    try:
        storage_state_path = resolve_storage_state_path(adapter)
    except FileNotFoundError as error:
        profile_dir_paths = getattr(adapter, "profile_dir_paths", None)

        if profile_dir_paths:
            profile_candidates = ", ".join(str(path) for path in profile_dir_paths())
            raise FileNotFoundError(
                f"No saved browser profile or storage state found for "
                f"{adapter.display_name}. Expected profile: "
                f"{profile_candidates}. Legacy storage fallback was also "
                "missing."
            ) from error

        raise

    browser = playwright.chromium.launch(
        channel="chrome",
        headless=False
    )
    context = browser.new_context(
        storage_state=str(storage_state_path)
    )
    return context, browser


def current_profile_path(adapter: ReviewSubmissionAdapter) -> str:
    profile_dir = resolve_profile_dir(adapter)

    if profile_dir:
        return str(profile_dir)

    try:
        return str(resolve_storage_state_path(adapter))
    except FileNotFoundError:
        return "unresolved"


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
    inserted_text = get_editor_text(locator)

    if len(inserted_text) < len(value or ""):
        locator.click()
        clear_editor(page)
        insert_text_in_chunks(
            page=page,
            text=value or "",
        )
        inserted_text = get_editor_text(locator)

    if len(inserted_text) < len(value or ""):
        raise RuntimeError(
            "Platform title insertion failed: inserted "
            f"{len(inserted_text)} of {len(value or '')} characters"
        )

    return len(inserted_text)


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


def wait_for_any_visible(
    page: Page,
    selectors: list[str],
    timeout: int = 30000,
):
    deadline = time.monotonic() + (timeout / 1000)
    last_error = None

    while time.monotonic() < deadline:
        for selector in selectors:
            try:
                locator = page.locator(selector).first

                if locator.count() and locator.is_visible(timeout=1000):
                    return locator
            except Exception as error:
                last_error = error

        time.sleep(0.5)

    raise RuntimeError(
        "No expected visible element found. Selectors: "
        f"{', '.join(selectors)}. Last error: {last_error}"
    )


def wait_for_optional_visible(
    page: Page,
    selectors: list[str],
    timeout: int = 5000,
):
    try:
        return wait_for_any_visible(
            page=page,
            selectors=selectors,
            timeout=timeout,
        )
    except RuntimeError:
        return None


def extract_creator_nickname(page: Page) -> str | None:
    selectors = [
        ".user-name",
        ".nickname",
        ".creator-name",
        "[class*='user'] [class*='name']",
        "[class*='avatar'] + *",
        "[class*='profile'] [class*='name']",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if locator.count() and locator.is_visible(timeout=1000):
                text = (locator.inner_text(timeout=1000) or "").strip()

                if text:
                    return text.splitlines()[0].strip()
        except Exception:
            continue

    return None
