import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.session_resolver import SessionResolver


PLATFORM_LOGIN_URLS = {
    ("reddit", None): "https://www.reddit.com/login/",
    ("xiaohongshu", "creator"): "https://creator.xiaohongshu.com/",
    ("xiaohongshu", "web"): "https://www.rednote.com/",
}


def main():
    parser = argparse.ArgumentParser(
        description="Save Playwright login state for a publishing platform."
    )
    parser.add_argument(
        "platform",
        choices=sorted({platform for platform, _ in PLATFORM_LOGIN_URLS}),
        help="Publishing platform to authenticate.",
    )
    parser.add_argument(
        "--purpose",
        choices=["creator", "web"],
        default=None,
        help=(
            "Session purpose. Xiaohongshu uses creator for publishing and "
            "web for retrieval."
        ),
    )
    args = parser.parse_args()
    purpose = args.purpose

    if args.platform == "xiaohongshu" and purpose is None:
        purpose = "creator"
    elif args.platform != "xiaohongshu":
        purpose = None

    login_url = PLATFORM_LOGIN_URLS.get((args.platform, purpose))

    if not login_url:
        raise SystemExit(
            f"No login URL configured for platform={args.platform} "
            f"purpose={purpose}"
        )

    resolver = SessionResolver()

    with sync_playwright() as playwright:
        if args.platform == "xiaohongshu":
            profile_dir = resolver.canonical_profile_dir(
                platform=args.platform,
                purpose=purpose,
            )
            profile_dir.mkdir(
                parents=True,
                exist_ok=True,
            )
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                channel="chrome",
                headless=False,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(login_url)

            print(
                f"Log in to {args.platform} ({purpose}) "
                "in the browser window."
            )
            input(
                "Press Enter here after login succeeds..."
            )

            print(
                f"Persistent profile kept at {profile_dir}"
            )
            context.close()
            return

        state_path = resolver.canonical_storage_state_path(
            platform=args.platform,
            purpose=purpose,
        )
        state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        browser = playwright.chromium.launch(
            channel="chrome",
            headless=False
        )
        context = browser.new_context()
        page = context.new_page()

        page.goto(
            login_url
        )

        print(
            f"Log in to {args.platform} ({purpose or 'default'}) "
            "in the browser window."
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
