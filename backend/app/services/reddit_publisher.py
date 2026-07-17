from pathlib import Path

from playwright.sync_api import Page

from app.services.platform_review_browser import (
    fill_first_visible,
    insert_into_first_visible_editor,
    publish_with_review_adapter,
)
from app.services.session_resolver import SessionResolver


class RedditSubmissionAdapter:
    platform = "reddit"
    display_name = "Reddit"
    clipboard_origin = "https://www.reddit.com"

    def __init__(self, session_path: str):
        self.session_path = Path(session_path)

    def profile_dir_paths(self) -> list[Path]:
        return SessionResolver().profile_candidate_paths(
            platform=self.platform,
            profile_path=self.session_path,
        )

    def storage_state_paths(self) -> list[Path]:
        return SessionResolver().storage_state_candidate_paths(
            platform=self.platform,
            session_path=self.session_path,
        )

    def open_submission_page(self, page: Page, target: str) -> None:
        subreddit = target or "test"
        page.goto(
            f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT"
        )

    def fill_title(self, page: Page, title: str) -> None:
        fill_first_visible(
            page=page,
            selectors=['textarea[name="title"]'],
            value=title,
        )

    def fill_body(self, page: Page, body: str) -> int:
        return insert_into_first_visible_editor(
            page=page,
            selectors=['[contenteditable="true"]'],
            body=body,
        )

    def preview_target(self, target: str) -> str:
        return target or "test"


def publish_to_reddit(
    username: str,
    password: str,
    subreddit: str,
    title: str,
    body: str,
    session_path: str,
):
    return publish_with_review_adapter(
        adapter=RedditSubmissionAdapter(session_path=session_path),
        target=subreddit,
        title=title,
        body=body,
    )
