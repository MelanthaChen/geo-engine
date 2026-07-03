import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.session_resolver import SessionResolver


PLATFORM_LOGIN_URLS = {
    "reddit": "https://www.reddit.com/login/",
    "xiaohongshu": "https://creator.xiaohongshu.com/",
}


def main():
    parser = argparse.ArgumentParser(
        description="Save Playwright login state for a publishing platform."
    )
    parser.add_argument(
        "platform",
        choices=sorted(PLATFORM_LOGIN_URLS),
        help="Publishing platform to authenticate.",
    )
    args = parser.parse_args()

    state_path = SessionResolver().canonical_path(args.platform)
    state_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False
        )
        context = browser.new_context()
        page = context.new_page()

        page.goto(
            PLATFORM_LOGIN_URLS[args.platform]
        )

        print(
            f"Log in to {args.platform} in the browser window."
        )
        input(
            "Press Enter here after login succeeds..."
        )

        context.storage_state(
            path=str(state_path)
        )

        print(
            f"{state_path} saved"
        )

        browser.close()


if __name__ == "__main__":
    main()
