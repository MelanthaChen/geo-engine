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
            headless=True
        )

        page = browser.new_page()

        #
        # Open Reddit login page
        #

        page.goto(
            "https://www.reddit.com/login/"
        )

        page.wait_for_timeout(5000)

        print(page.title())

        print(page.url)

        page.screenshot(
            path="reddit_login.png"
        )

        print(page.content()[:5000])

        #
        # Fill username
        #

        username_input = page.locator(
            'input[name="username"]'
        )

        username_input.click()

        username_input.fill(username)

        #
        # Fill password
        #

        password_input = page.locator(
            'input[name="password"]'
        )

        password_input.click()

        password_input.fill(password)

        #
        # Click login button
        #

        login_button = page.get_by_role(
            "button",
            name="Log In"
        )

        login_button.click()

        #
        # Wait after login
        #

        page.wait_for_timeout(8000)

        #
        # Open Reddit submit page
        #

        page.goto(
            f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT"
        )

        #
        # Wait for page load
        #

        page.wait_for_timeout(8000)

        #
        # Fill title
        #

        title_box = page.locator(
            'textarea[name="title"]'
        )

        title_box.wait_for(
            state="visible",
            timeout=15000
        )

        title_box.click()

        page.wait_for_timeout(1000)

        title_box.fill(title)

        page.wait_for_timeout(2000)

        #
        # Fill body
        #

        body_editor = page.get_by_role(
            "textbox",
            name="Post body text field"
        )

        body_editor.click()

        page.wait_for_timeout(1000)

        body_editor.fill(body)

        page.wait_for_timeout(3000)

        #
        # Click Post button
        #

        post_button = page.get_by_role(
            "button",
            name="Post"
        )

        post_button.wait_for(
            state="visible",
            timeout=15000
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