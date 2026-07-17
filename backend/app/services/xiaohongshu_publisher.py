from pathlib import Path

from playwright.sync_api import Page

from app.services.platform_review_browser import (
    fill_first_visible,
    insert_into_first_visible_editor,
    publish_with_review_adapter,
    wait_for_any_visible,
)
from app.services.session_resolver import SessionResolver


class XiaohongshuSubmissionAdapter:
    platform = "xiaohongshu"
    display_name = "Xiaohongshu"
    clipboard_origin = "https://creator.rednote.com"
    publish_url = "https://creator.xiaohongshu.com/publish/publish?source=official"
    placeholder_image_path = (
        Path(__file__).resolve().parents[2] /
        "publishing_previews" /
        "xiaohongshu_dom_inspection" /
        "test_upload_image.png"
    )

    def __init__(self, session_path: str | None = None):
        self.session_path = session_path

    def storage_state_paths(self) -> list[Path]:
        return SessionResolver().storage_state_candidate_paths(
            platform=self.platform,
            purpose="creator",
        )

    def profile_dir_paths(self) -> list[Path]:
        return SessionResolver().profile_candidate_paths(
            platform=self.platform,
            purpose="creator",
        )

    def open_submission_page(self, page: Page, target: str) -> None:
        print("Opening Xiaohongshu Creator Center...")
        page.goto(
            "https://creator.xiaohongshu.com/",
            wait_until="domcontentloaded",
        )
        self.wait_until_navigation_settles(page)

        if self.is_publish_page(page):
            print("Publish page detected.")
            return

        self.verify_creator_login(page)
        print("Creator Center detected.")

        print("Publish page opened.")
        page.goto(
            self.publish_url,
            wait_until="domcontentloaded",
        )
        self.wait_until_navigation_settles(page)

        if self.is_publish_page(page):
            print("Publish page detected.")

    def wait_until_ready(self, page: Page) -> None:
        print("Waiting for editor...")
        if not self.is_publish_page(page):
            self.verify_creator_login(page)
        self.switch_to_graphic_tab(page)
        self.upload_placeholder_image(page)
        self.wait_for_editor_after_upload(page)
        self.wait_for_title_input(page)
        self.wait_for_body_editor(page)

    def wait_until_navigation_settles(self, page: Page) -> None:
        last_url = None

        for _ in range(45):
            if self.is_publish_page(page):
                print("Publish page detected.")
                return

            if page.url != last_url:
                last_url = page.url
                print(f"Startup navigation URL: {last_url}")

            page.wait_for_timeout(1000)

        if self.is_publish_page(page):
            print("Publish page detected.")
            return

        print(f"Startup navigation settled without publish page: {page.url}")

    def is_publish_page(self, page: Page) -> bool:
        current_url = page.url.lower()

        return (
            "creator.rednote.com/publish/publish" in current_url
            or "creator.xiaohongshu.com/publish/publish" in current_url
        )

    def verify_creator_login(self, page: Page) -> None:
        creator_ui_selectors = [
            "text=发布",
            "text=创作中心",
            "text=首页",
            "text=笔记",
            "text=数据",
            "text=账号",
            "[class*='creator']",
            "[class*='publish']",
            "a[href*='/publish']",
        ]

        try:
            wait_for_any_visible(
                page=page,
                selectors=creator_ui_selectors,
                timeout=45000,
            )
            return
        except RuntimeError:
            pass

        login_indicators = [
            "text=扫码登录",
            "text=登录",
            "text=验证码",
            "text=手机号",
            "input[placeholder*='手机号']",
            "input[placeholder*='验证码']",
            "[class*='login']",
        ]

        for selector in login_indicators:
            try:
                locator = page.locator(selector).first

                if locator.count() and locator.is_visible(timeout=1000):
                    raise RuntimeError(
                        "Xiaohongshu Creator Center login is invalid or "
                        "expired. Recreate the creator profile with: "
                        "python save_platform_state.py xiaohongshu "
                        "--purpose creator"
                    )
            except RuntimeError:
                raise
            except Exception:
                continue

        raise RuntimeError(
            "Xiaohongshu Creator Center did not expose a recognized "
            "logged-in creator UI. Confirm the creator profile is logged in: "
            "python save_platform_state.py xiaohongshu --purpose creator"
        )

    def wait_for_title_input(self, page: Page):
        return wait_for_any_visible(
            page=page,
            selectors=self.title_selectors(),
            timeout=45000,
        )

    def wait_for_body_editor(self, page: Page):
        return wait_for_any_visible(
            page=page,
            selectors=self.body_selectors(),
            timeout=45000,
        )

    def click_robustly(self, page: Page, locator, label: str) -> None:
        locator.scroll_into_view_if_needed(timeout=10000)
        try:
            locator.hover(timeout=10000)
        except Exception as hover_error:
            print(f"{label} hover failed; continuing: {hover_error}")

        try:
            locator.click(timeout=10000)
            print(f"{label} click strategy succeeded: normal")
            return
        except Exception as normal_error:
            print(f"{label} normal click failed: {normal_error}")

        try:
            locator.click(force=True, timeout=10000)
            print(f"{label} click strategy succeeded: force")
            return
        except Exception as force_error:
            print(f"{label} force click failed: {force_error}")

        element = locator.element_handle(timeout=10000)
        if not element:
            raise RuntimeError(f"{label} click failed: no element handle")
        page.evaluate("(el) => el.click()", element)
        print(f"{label} click strategy succeeded: dom")

    def switch_to_graphic_tab(self, page: Page) -> None:
        print("Switching to 上传图文...")
        page.wait_for_load_state("domcontentloaded")

        click_target = page.evaluate(
            """() => {
                const visible = (element) => {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        rect.width > 0 &&
                        rect.height > 0 &&
                        Number(style.opacity || 1) > 0.01;
                };
                const tabs = Array.from(document.querySelectorAll(
                    '#creator-publish-dom .header-tabs .creator-tab'
                )).filter((element) =>
                    visible(element) &&
                    (element.innerText || element.textContent || '').includes('上传图文')
                );
                const target = tabs.at(-1);
                if (!target) {
                    return null;
                }
                const rect = target.getBoundingClientRect();
                return {
                    x: rect.x + rect.width / 2,
                    y: rect.y + rect.height / 2,
                    text: (target.innerText || target.textContent || '').trim(),
                };
            }"""
        )

        if not click_target:
            tab_locator = wait_for_any_visible(
                page=page,
                selectors=[
                    '#creator-publish-dom .header-tabs .creator-tab:has-text("上传图文")',
                    'text=上传图文',
                ],
                timeout=30000,
            )
            self.click_robustly(page, tab_locator, "上传图文 tab")
        else:
            tab_locator = page.locator(
                '#creator-publish-dom .header-tabs .creator-tab'
            ).filter(has_text="上传图文").last
            self.click_robustly(page, tab_locator, "上传图文 tab")

        page.wait_for_function(
            """() => {
                const text = document.body.innerText || '';
                return text.includes('上传图片，或写文字生成图片') ||
                    text.includes('上传图片') ||
                    Boolean(document.querySelector('input.upload-input[type="file"]'));
            }""",
            timeout=45000,
        )
        print("上传图文 tab ready.")

    def upload_placeholder_image(self, page: Page) -> None:
        image_path = self.placeholder_image_path

        if not image_path.exists():
            raise FileNotFoundError(
                "Xiaohongshu placeholder image is missing. Expected: "
                f"{image_path}"
            )

        upload_input = page.locator('input.upload-input[type="file"]').first
        upload_input.set_input_files(str(image_path))
        print(f"image uploaded=true path={image_path}")

    def wait_for_editor_after_upload(self, page: Page) -> None:
        print("Waiting for Xiaohongshu editor after image upload...")
        page.wait_for_function(
            """() => {
                const text = document.body.innerText || '';
                const titleInput = Boolean(
                    document.querySelector('input[placeholder*="填写标题会有更多赞哦"]')
                );
                const bodyEditor = Boolean(
                    document.querySelector('div[role="textbox"].tiptap.ProseMirror')
                );
                const publishButton = Boolean(
                    document.querySelector('xhs-publish-btn[submit-text*="发布"]')
                );
                const uploadStillVisible = text.includes('上传图片，或写文字生成图片');
                const progressVisible = text.includes('上传中') ||
                    text.includes('处理中') ||
                    text.includes('%');

                window.__geoXhsEditorState = {
                    titleInput,
                    bodyEditor,
                    publishButton,
                    uploadStillVisible,
                    progressVisible,
                };

                return titleInput && bodyEditor && publishButton && !progressVisible;
            }""",
            timeout=90000,
        )
        state = page.evaluate("() => window.__geoXhsEditorState || null")
        print(f"Xiaohongshu editor mounted: {state}")

    def title_selectors(self) -> list[str]:
        return [
            'input[placeholder*="填写标题会有更多赞哦"]',
            'input[placeholder*="标题"]',
            'textarea[placeholder*="标题"]',
            'input[aria-label*="标题"]',
            'textarea[aria-label*="标题"]',
            '[contenteditable="true"][data-placeholder*="标题"]',
            '[contenteditable="true"][placeholder*="标题"]',
            '[class*="title"] input',
            '[class*="title"] textarea',
            '[class*="Title"] input',
            '[class*="Title"] textarea',
        ]

    def body_selectors(self) -> list[str]:
        return [
            'div[role="textbox"].tiptap.ProseMirror',
            'textarea[placeholder*="正文"]',
            'textarea[placeholder*="描述"]',
            'textarea[placeholder*="分享"]',
            '[contenteditable="true"][data-placeholder*="正文"]',
            '[contenteditable="true"][data-placeholder*="描述"]',
            '[contenteditable="true"][data-placeholder*="分享"]',
            '[contenteditable="true"][placeholder*="正文"]',
            '[contenteditable="true"][placeholder*="描述"]',
            '[class*="editor"] [contenteditable="true"]',
            '[class*="Editor"] [contenteditable="true"]',
            '[class*="content"] textarea',
            '[class*="Content"] textarea',
            '[contenteditable="true"]',
        ]

    def fill_title(self, page: Page, title: str) -> int:
        inserted_chars = fill_first_visible(
            page=page,
            selectors=self.title_selectors(),
            value=title,
        )
        print("Title inserted.")
        return inserted_chars

    def fill_body(self, page: Page, body: str) -> int:
        inserted_chars = insert_into_first_visible_editor(
            page=page,
            selectors=self.body_selectors(),
            body=body,
        )
        print("Body inserted.")
        return inserted_chars

    def wait_until_review_ready(self, page: Page) -> bool:
        page.wait_for_function(
            """() => {
                const publishButton = document.querySelector(
                    'xhs-publish-btn[submit-text*="发布"]'
                );
                if (!publishButton) {
                    return false;
                }
                const submitDisabled = publishButton.getAttribute('submit-disabled');
                const ariaDisabled = publishButton.getAttribute('aria-disabled');
                const disabled = publishButton.hasAttribute('disabled');
                return submitDisabled !== 'true' &&
                    ariaDisabled !== 'true' &&
                    !disabled;
            }""",
            timeout=30000,
        )
        print("publish enabled=true")
        return True

    def review_screenshot_path(self) -> Path:
        preview_dir = Path("publishing_previews")
        preview_dir.mkdir(exist_ok=True)
        return preview_dir / "review_ready.png"

    def preview_target(self, target: str) -> str:
        return target or "xiaohongshu"


def publish_to_xiaohongshu(
    title: str,
    body: str,
    target: str = "xiaohongshu",
    session_path: str | None = None,
):
    return publish_with_review_adapter(
        adapter=XiaohongshuSubmissionAdapter(session_path=session_path),
        target=target,
        title=title,
        body=body,
    )
