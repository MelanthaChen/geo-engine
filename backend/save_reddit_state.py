from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    context = browser.new_context()

    page = context.new_page()

    page.goto(
        "https://www.reddit.com/login/"
    )

    print(
        "Login successful，bacl to terminal Enter"
    )

    input()

    context.storage_state(
        path="reddit_state.json"
    )

    print(
        "reddit_state.json saved"
    )

    browser.close()