from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir="./tmp_reddit_profile",
            channel="chrome",
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto("https://www.reddit.com/")
        page.wait_for_timeout(5000)
        print("HOME URL:", page.url)
        print("HOME TITLE:", page.title())
        page.screenshot(path="reddit_persistent_home.png", full_page=True)

        page.goto("https://www.reddit.com/login/")
        page.wait_for_timeout(5000)
        print("LOGIN URL:", page.url)
        print("LOGIN TITLE:", page.title())
        page.screenshot(path="reddit_persistent_login.png", full_page=True)

        input("Press ENTER to close browser...")
        context.close()


if __name__ == "__main__":
    main()
