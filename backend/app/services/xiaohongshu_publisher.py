from pathlib import Path

from playwright.sync_api import Page

from app.services.platform_review_browser import (
    fill_first_visible,
    insert_into_first_visible_editor,
    publish_with_review_adapter,
)


class XiaohongshuSubmissionAdapter:
    platform = "xiaohongshu"
    display_name = "Xiaohongshu"
    clipboard_origin = "https://creator.xiaohongshu.com"

    def __init__(self, session_path: str | None = None):
        self.session_path = session_path

    def storage_state_paths(self) -> list[Path]:
        paths = [
            Path("sessions/xiaohongshu/storage_state.json"),
            Path("xiaohongshu_state.json"),
        ]

        if self.session_path:
            paths.insert(0, Path(self.session_path))

        return paths

    def open_submission_page(self, page: Page, target: str) -> None:
        page.goto(
            "https://creator.xiaohongshu.com/publish/publish?source=official"
        )

    def fill_title(self, page: Page, title: str) -> None:
        fill_first_visible(
            page=page,
            selectors=[
                'input[placeholder*="标题"]',
                'textarea[placeholder*="标题"]',
                'input[aria-label*="标题"]',
                '[contenteditable="true"][data-placeholder*="标题"]',
            ],
            value=title,
        )

    def fill_body(self, page: Page, body: str) -> int:
        return insert_into_first_visible_editor(
            page=page,
            selectors=[
                'textarea[placeholder*="正文"]',
                'textarea[placeholder*="描述"]',
                '[contenteditable="true"][data-placeholder*="正文"]',
                '[contenteditable="true"][data-placeholder*="描述"]',
                '[contenteditable="true"]',
            ],
            body=body,
        )

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
