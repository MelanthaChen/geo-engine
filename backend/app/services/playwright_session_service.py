from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session

from app.models.account import Account
from app.services.session_resolver import SessionResolver


PLATFORM_LOGIN_URLS = {
    "reddit": "https://www.reddit.com/login/",
    "xiaohongshu": "https://creator.xiaohongshu.com/",
}


class PlaywrightSessionService:
    def __init__(
        self,
        db: Session | None = None,
    ):
        self.db = db
        self.session_resolver = SessionResolver()

    def locate_storage_path(self, account: Account) -> Path:
        platform = (account.platform or "reddit").strip().lower()
        return self.session_resolver.canonical_path(platform)

    def load_session(self, account: Account) -> str:
        session_path = account.session_path

        if not session_path:
            raise RuntimeError(
                f"Account {account.handle} does not have a Playwright session path."
            )

        path = self.session_resolver.resolve(
            platform=account.platform,
            session_path=session_path,
        )

        return str(path)

    def load_session_path(
        self,
        session_path: str | Path,
        platform: str = "reddit",
    ) -> str:
        path = self.session_resolver.resolve(
            platform=platform,
            session_path=session_path,
        )

        return str(path)

    def create_session(self, account: Account) -> Path:
        platform = (account.platform or "reddit").strip().lower()
        login_url = PLATFORM_LOGIN_URLS.get(platform)

        if not login_url:
            raise RuntimeError(
                f"No login URL configured for platform: {platform}"
            )

        session_path = self.locate_storage_path(account)
        session_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(login_url)

            print(
                f"Login to {platform} for account {account.handle}, "
                "then press Enter here."
            )
            input()

            context.storage_state(path=str(session_path))
            browser.close()

        now = self._now()
        account.session_path = str(session_path)
        account.state_identifier = str(session_path)
        account.session_status = "active"
        account.last_login = now
        account.last_session_refresh = now
        account.last_session_validation = now
        account.browser_profile_name = account.browser_profile_name or self._slugify(
            account.handle or f"account-{account.id}"
        )

        self._commit(account)
        return session_path

    def refresh_session(self, account: Account) -> None:
        account.last_session_refresh = self._now()
        account.session_status = account.session_status or "active"
        self._commit(account)

    def validate_session(self, account: Account) -> bool:
        try:
            self.load_session(account)
        except (FileNotFoundError, RuntimeError):
            account.session_status = "missing"
            account.last_session_validation = self._now()
            self._commit(account)
            return False

        account.session_status = "active"
        account.last_session_validation = self._now()
        self._commit(account)
        return True

    def delete_session(self, account: Account) -> None:
        path = self.locate_storage_path(account)
        if path.exists():
            path.unlink()

        account.session_path = None
        account.session_status = "missing"
        account.last_session_validation = self._now()
        self._commit(account)

    def _commit(self, account: Account) -> None:
        if not self.db:
            return

        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
        return slug.strip("-") or "account"
