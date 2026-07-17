from datetime import datetime
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

from app.services.platform_review_browser import launch_review_context
from app.services.xiaohongshu_publisher import XiaohongshuSubmissionAdapter


PUBLISH_URL = "https://creator.rednote.com/publish/publish"
OUTPUT_DIR = Path("publishing_previews") / "xiaohongshu_creator_profile"


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def safe_page_snapshot(page):
    try:
        return page.evaluate(
            """() => ({
                readyState: document.readyState,
                bodyText: (document.body?.innerText || '').slice(0, 200),
            })"""
        )
    except Exception as error:
        return {
            "readyState": f"<error {type(error).__name__}: {error}>",
            "bodyText": "",
        }


def safe_title(page):
    try:
        return page.title()
    except Exception as error:
        return f"<error {type(error).__name__}: {error}>"


def classify_page(page):
    url = page.url.lower()
    snapshot = safe_page_snapshot(page)
    body_text = snapshot["bodyText"]

    if "/publish/publish" in url and not is_login_text(body_text):
        return "Publish page"

    if "/login" in url or is_login_text(body_text):
        return "Login page"

    return "Unknown page"


def is_login_text(text: str):
    return any(
        marker in text
        for marker in (
            "短信登录",
            "扫码登录",
            "发送验证码",
            "登录即同意",
        )
    )


def print_page_state(page, label):
    snapshot = safe_page_snapshot(page)
    print(
        f"[{timestamp()}] {label} "
        f"url={page.url} "
        f"title={safe_title(page)!r} "
        f"readyState={snapshot['readyState']} "
        f"bodyText={snapshot['bodyText']!r}",
        flush=True,
    )


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    adapter = XiaohongshuSubmissionAdapter()

    with sync_playwright() as playwright:
        context, _browser = launch_review_context(
            playwright=playwright,
            adapter=adapter,
        )

        try:
            print(
                f"[{timestamp()}] context.pages.count={len(context.pages)}",
                flush=True,
            )
            print(
                f"[{timestamp()}] context.browser.version="
                f"{context.browser.version if context.browser else None}",
                flush=True,
            )

            page = context.pages[0] if context.pages else context.new_page()

            def log_first_401(response):
                if response.status != 401:
                    return

                print(
                    f"[{timestamp()}] FIRST_401_REQUEST",
                    flush=True,
                )
                print(
                    f"URL: {response.url}",
                    flush=True,
                )
                print(
                    f"Method: {response.request.method}",
                    flush=True,
                )
                print(
                    f"Status: {response.status}",
                    flush=True,
                )
                try:
                    headers = response.headers
                except Exception as error:
                    headers = {
                        "header_error": f"{type(error).__name__}: {error}",
                    }
                print(
                    f"Response headers: {headers}",
                    flush=True,
                )
                raise SystemExit(0)

            def log_redirect(request):
                redirected_from = request.redirected_from

                if redirected_from:
                    print(
                        f"[{timestamp()}] REDIRECT "
                        f"from={redirected_from.url} "
                        f"to={request.url}",
                        flush=True,
                    )

            page.on("response", log_first_401)
            page.on("request", log_redirect)
            page.on(
                "framenavigated",
                lambda frame: (
                    frame == page.main_frame
                    and print_page_state(page, "NAVIGATED")
                ),
            )

            print(
                f"[{timestamp()}] Opening direct publish URL: {PUBLISH_URL}",
                flush=True,
            )
            page.goto(
                PUBLISH_URL,
                wait_until="domcontentloaded",
            )

            for second in range(31):
                print_page_state(page, f"t={second}s")

                classification = classify_page(page)
                print(
                    f"[{timestamp()}] classification={classification}",
                    flush=True,
                )

                if second < 30:
                    page.wait_for_timeout(1000)

            screenshot_path = OUTPUT_DIR / "creator_profile_direct_publish.png"
            html_path = OUTPUT_DIR / "creator_profile_direct_publish.html"

            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )
            html_path.write_text(
                page.content(),
                encoding="utf-8",
            )

            print(
                f"[{timestamp()}] final_classification={classify_page(page)}",
                flush=True,
            )
            print(
                f"[{timestamp()}] screenshot={screenshot_path}",
                flush=True,
            )
            print(
                f"[{timestamp()}] html={html_path}",
                flush=True,
            )
        finally:
            context.close()


if __name__ == "__main__":
    main()
