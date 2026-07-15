from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.session_resolver import SessionResolver


def main():
    resolver = SessionResolver()
    profile_dir = resolver.canonical_profile_dir(
        platform="xiaohongshu",
        purpose="web",
    )
    profile_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"Profile path: {profile_dir}")
    print("Run 1: log in if prompted, then close the browser window.")
    run_profile_check(
        profile_dir=profile_dir,
        wait_for_manual_close=True,
    )

    print("\nRun 2: reopening the same profile.")
    result = run_profile_check(
        profile_dir=profile_dir,
        wait_for_manual_close=False,
    )

    print("\nVerification result")
    print(f"Current URL: {result['url']}")
    print(f"Current logged-in account nickname: {result['nickname'] or 'unknown'}")
    print(f"Cookie count: {result['cookie_count']}")
    print(f"Profile path: {profile_dir}")
    print(f"Login prompt visible: {result['login_prompt_visible']}")
    print(
        "No QR login required on run 2: "
        f"{'yes' if not result['login_prompt_visible'] else 'no'}"
    )


def run_profile_check(
    profile_dir: Path,
    wait_for_manual_close: bool,
):
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=False,
            locale="zh-CN",
            viewport={"width": 1440, "height": 1100},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(
            "https://www.rednote.com/",
            wait_until="commit",
            timeout=30000,
        )
        page.wait_for_timeout(5000)

        result = inspect_login_state(
            context=context,
            page=page,
        )

        if wait_for_manual_close:
            print(f"Current URL: {result['url']}")
            print(f"Current logged-in account nickname: {result['nickname'] or 'unknown'}")
            print(f"Cookie count: {result['cookie_count']}")
            print("Close the browser window after login is complete.")
            wait_until_closed(context)
        else:
            context.close()

        return result


def inspect_login_state(context, page):
    cookies = context.cookies()
    snapshot = page.evaluate(
        """
        () => {
          const text = document.body?.innerText || '';
          const loginPromptVisible = /登录|扫码|验证码/.test(text) &&
            !/(我|通知|发布)/.test(text.slice(0, 500));
          const candidates = Array.from(
            document.querySelectorAll(
              '[class*="nickname"], [class*="user"], [class*="name"], a[href*="/user/profile/"]'
            )
          ).map((node) => (node.innerText || node.textContent || '').trim())
           .filter(Boolean)
           .filter((value) => value.length <= 40);
          return {
            url: location.href,
            nickname: candidates[0] || '',
            loginPromptVisible,
          };
        }
        """
    )

    return {
        "url": snapshot["url"],
        "nickname": snapshot["nickname"],
        "login_prompt_visible": snapshot["loginPromptVisible"],
        "cookie_count": len(cookies),
    }


def wait_until_closed(context):
    while True:
        pages = [page for page in context.pages if not page.is_closed()]

        if not pages:
            return

        pages[0].wait_for_timeout(1000)


if __name__ == "__main__":
    main()
