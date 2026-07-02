from pathlib import Path

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
        "Login to Reddit in the browser, then press Enter here."
    )

    input()

    state_path = Path("sessions/reddit/storage_state.json")
    state_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    context.storage_state(
        path=str(state_path)
    )
    context.storage_state(
        path="reddit_state.json"
    )

    print(
        f"{state_path} saved"
    )
    print(
        "reddit_state.json saved for backwards compatibility"
    )

    browser.close()
