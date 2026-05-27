from playwright.sync_api import (
    sync_playwright
)


def publish_to_reddit(
    username: str,
    password: str,
    subreddit: str,
    title: str,
    body: str,
):

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            slow_mo=500
        )

        page = browser.new_page()

        #
        # Open Reddit login page
        #

        page.goto(
            "https://www.reddit.com/login/"
        )

        page.wait_for_timeout(5000)

        #
        # Fill username
        #

        page.locator(
            'input[name="username"]'
        ).fill(username)

        #
        # Fill password
        #

        page.locator(
            'input[name="password"]'
        ).fill(password)

        #
        # Click login
        #

        page.get_by_role(
            "button",
            name="Log In"
        ).click()

        #
        # Wait after login
        #

        page.wait_for_timeout(8000)

        #
        # Open subreddit submit page
        #

        page.goto(
            f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT"
        )

        page.wait_for_timeout(8000)

        #
        # Click title field
        #

        page.mouse.click(520, 435)

        page.wait_for_timeout(1000)

        #
        # Type title
        #

        page.keyboard.type(title)

        page.wait_for_timeout(2000)

        #
        # Click body editor
        #

        body_editor = page.locator(
            '[contenteditable="true"]'
        ).last

        body_editor.click()

        page.wait_for_timeout(1000)

        #
        # Type body
        #

        page.keyboard.type(body)

        page.wait_for_timeout(3000)

        #
        # Click Post button
        #

        post_button = page.get_by_role(
            "button",
            name="Post"
        )

        post_button.click()

        #
        # Wait after posting
        #

        page.wait_for_timeout(8000)

        current_url = page.url

        browser.close()

        return {
            "url": current_url
        }