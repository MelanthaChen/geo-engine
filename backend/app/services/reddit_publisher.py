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

        page.goto(
            f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT",
            wait_until="networkidle",
            timeout=60000
        )

        print("=" * 50)

        print("URL:")
        print(page.url)

        print("=" * 50)

        print("TITLE:")
        print(page.title())

        print("=" * 50)

        content = page.content()

        print(content[:5000])

        print("=" * 50)

        browser.close()

        return {
            "url": page.url,
            "title": page.title()
        }