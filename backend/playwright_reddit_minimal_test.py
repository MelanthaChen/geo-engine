from playwright.sync_api import sync_playwright


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=False,
            ignore_default_args=[
                "--enable-automation",
                "--disable-extensions",
                "--disable-component-extensions-with-background-pages",
                "--disable-default-apps",
                "--no-sandbox",
            ],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
            viewport={"width": 1440, "height": 900},
            screen={"width": 1440, "height": 900},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = window.chrome || {};
            window.chrome.runtime = window.chrome.runtime || {};
            """
        )
        page = context.new_page()

        page.goto("https://www.reddit.com/")
        page.wait_for_timeout(5000)
        print("HOME URL:", page.url)
        print("HOME TITLE:", page.title())
        page.screenshot(path="reddit_home.png", full_page=True)

        page.goto("https://www.reddit.com/login/")
        page.wait_for_timeout(5000)
        print("LOGIN URL:", page.url)
        print("LOGIN TITLE:", page.title())
        page.screenshot(path="reddit_login.png", full_page=True)

        input("Press ENTER to close browser...")
        browser.close()


if __name__ == "__main__":
    main()
