import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.session_resolver import SessionResolver


PLATFORM_LOGIN_URLS = {
    ("reddit", None): "https://www.reddit.com/login/",
    ("xiaohongshu", "creator"): "https://creator.xiaohongshu.com/",
    ("xiaohongshu", "web"): "https://www.rednote.com/",
}

CREATOR_PUBLISH_URLS = [
    "https://creator.rednote.com/publish/publish",
    "https://creator.xiaohongshu.com/publish/publish",
]


def inspect_creator_publish_state(page):
    return page.evaluate(
        """() => {
            const text = document.body?.innerText || '';
            const exists = (selector) => Boolean(document.querySelector(selector));
            const url = window.location.href;

            return {
                url,
                title: document.title,
                readyState: document.readyState,
                isLoginPage: url.includes('/login') ||
                    text.includes('短信登录') ||
                    text.includes('扫码登录') ||
                    text.includes('发送验证码'),
                isPublishPage: url.includes('/publish/publish'),
                publishShellExists: exists('#creator-publish-dom') ||
                    exists('[class*="publish"]'),
                uploadUiExists: exists('input.upload-input[type="file"]') ||
                    exists('.drag-over') ||
                    text.includes('上传图片') ||
                    text.includes('上传视频'),
                uploadTabExists: text.includes('上传图文') ||
                    Boolean(
                        Array.from(document.querySelectorAll('.creator-tab, [role="tab"], button'))
                            .some((element) =>
                                (element.innerText || element.textContent || '')
                                    .includes('上传图文')
                            )
                    ),
                bodyPreview: text.slice(0, 200),
            };
        }"""
    )


def wait_for_creator_publish_authorization(page):
    print("Waiting for Creator publish authorization...")
    last_url = None
    last_message = None
    next_publish_url_index = 0

    while True:
        try:
            state = inspect_creator_publish_state(page)
        except Exception as error:
            state = {
                "url": page.url,
                "title": "",
                "isLoginPage": True,
                "isPublishPage": False,
                "publishShellExists": False,
                "uploadUiExists": False,
                "uploadTabExists": False,
                "bodyPreview": f"inspection failed: {error}",
            }

        if state["url"] != last_url:
            last_url = state["url"]
            print(f"Current URL: {state['url']}")
            print(f"Current title: {state['title']}")

        publish_accessible = (
            state["isPublishPage"]
            and (
                state["publishShellExists"]
                or state["uploadUiExists"]
                or state["uploadTabExists"]
            )
        )

        if publish_accessible:
            print("Creator publish authorization verified.")
            return state

        if state["isLoginPage"]:
            message = "Publish authorization has not completed yet."
            if message != last_message:
                print(message)
                last_message = message
            page.wait_for_timeout(3000)
            continue

        if not state["isPublishPage"]:
            publish_url = CREATOR_PUBLISH_URLS[
                next_publish_url_index % len(CREATOR_PUBLISH_URLS)
            ]
            next_publish_url_index += 1
            print(f"Checking publish page authorization: {publish_url}")
            page.goto(
                publish_url,
                wait_until="domcontentloaded",
            )

        page.wait_for_timeout(3000)


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
        if args.platform in {"reddit", "xiaohongshu"}:
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

            if args.platform == "xiaohongshu" and purpose == "creator":
                verification_state = wait_for_creator_publish_authorization(page)
                print(
                    "Current URL: "
                    f"{verification_state['url']}"
                )
                print(
                    "Current title: "
                    f"{verification_state['title']}"
                )
                print(
                    "Publish page accessible: "
                    f"{verification_state['isPublishPage']}"
                )
                print(
                    "Upload UI exists: "
                    f"{verification_state['uploadUiExists']}"
                )
                print(
                    "Upload tab exists: "
                    f"{verification_state['uploadTabExists']}"
                )
                input(
                    "Press ENTER to save the profile..."
                )
            else:
                input(
                    "Press Enter here after login succeeds..."
                )

            print(
                f"Persistent profile kept at {profile_dir}"
            )
            context.close()
            return


if __name__ == "__main__":
    main()
