from playwright.sync_api import sync_playwright


def publish_to_reddit(
    username: str,
    password: str,
    subreddit: str,
    title: str,
    body: str,
):

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            storage_state="reddit_state.json"
        )

        page = context.new_page()

        #
        # Open submit page
        #

        page.goto(
            f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT",
            wait_until="domcontentloaded",
            timeout=60000
        )

        #
        # Give Reddit time to hydrate React
        #

        page.wait_for_timeout(15000)

        print("=" * 60)
        print("URL:")
        print(page.url)

        print("=" * 60)
        print("TITLE:")
        print(page.title())

        print("=" * 60)

        title_count = page.locator(
            'textarea[name="title"]'
        ).count()

        editor_count = page.locator(
            '[contenteditable="true"]'
        ).count()

        print(
            f"TITLE COUNT: {title_count}"
        )

        print(
            f"EDITOR COUNT: {editor_count}"
        )

        #
        # Save page source for debugging
        #

        with open(
            "/tmp/reddit_page.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                page.content()
            )

        page.screenshot(
            path="/tmp/reddit_debug.png"
        )

        current_url = page.url

        current_title = page.title()

        browser.close()

        return {
            "url": current_url,
            "title": current_title,
            "title_count": title_count,
            "editor_count": editor_count
        }