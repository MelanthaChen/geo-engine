from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session

from app.models.account import Account
from app.services.session_resolver import SessionResolver


PLATFORM_LOGIN_URLS = {
    ("reddit", None): "https://www.reddit.com/login/",
    ("perplexity", None): "https://www.perplexity.ai/",
    ("xiaohongshu", "creator"): "https://creator.xiaohongshu.com/",
    ("xiaohongshu", "web"): "https://www.rednote.com/",
}


class PlaywrightSessionService:
    def __init__(
        self,
        db: Session | None = None,
    ):
        self.db = db
        self.session_resolver = SessionResolver()

    def locate_storage_path(
        self,
        account: Account,
        purpose: str | None = None,
    ) -> Path:
        platform = (account.platform or "reddit").strip().lower()
        resolved_purpose = self.default_purpose(platform, purpose)

        if platform in {"reddit", "xiaohongshu", "perplexity"}:
            return self.session_resolver.canonical_profile_dir(
                platform=platform,
                purpose=resolved_purpose,
            )

        return self.session_resolver.canonical_storage_state_path(
            platform=platform,
            purpose=resolved_purpose,
        )

    def load_session(
        self,
        account: Account,
        purpose: str | None = None,
    ) -> str:
        platform = (account.platform or "reddit").strip().lower()
        resolved_purpose = self.default_purpose(platform, purpose)
        canonical_session_path = str(
            self.locate_storage_path(
                account=account,
                purpose=resolved_purpose,
            )
        )

        if resolved_purpose == "creator" and account.session_path != canonical_session_path:
            account.session_path = canonical_session_path
            account.state_identifier = canonical_session_path
            self._commit(account)

        session_path = (
            account.session_path
            if resolved_purpose == "creator"
            else canonical_session_path
        )

        if not session_path:
            raise RuntimeError(
                f"Account {account.handle} does not have a Playwright session path."
            )

        if platform in {"reddit", "xiaohongshu", "perplexity"}:
            path = self.session_resolver.resolve_profile(
                platform=account.platform,
                profile_path=session_path,
                purpose=resolved_purpose,
            )
        else:
            path = self.session_resolver.resolve_storage_state(
                platform=account.platform,
                session_path=session_path,
                purpose=resolved_purpose,
            )

        return str(path)

    def load_session_path(
        self,
        session_path: str | Path,
        platform: str = "reddit",
        purpose: str | None = None,
    ) -> str:
        resolved_purpose = self.default_purpose(platform, purpose)

        if platform in {"reddit", "xiaohongshu", "perplexity"}:
            try:
                path = self.session_resolver.resolve_profile(
                    platform=platform,
                    profile_path=session_path,
                    purpose=resolved_purpose,
                )
            except FileNotFoundError:
                path = self.session_resolver.resolve_storage_state(
                    platform=platform,
                    purpose=resolved_purpose,
                )
        else:
            path = self.session_resolver.resolve_storage_state(
                platform=platform,
                session_path=session_path,
                purpose=resolved_purpose,
            )

        return str(path)

    def create_session(
        self,
        account: Account,
        purpose: str | None = None,
    ) -> Path:
        platform = (account.platform or "reddit").strip().lower()
        resolved_purpose = self.default_purpose(platform, purpose)
        login_url = PLATFORM_LOGIN_URLS.get((platform, resolved_purpose))

        if not login_url:
            raise RuntimeError(
                f"No login URL configured for platform: {platform} "
                f"purpose: {resolved_purpose}"
            )

        session_path = self.locate_storage_path(
            account=account,
            purpose=resolved_purpose,
        )
        session_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            if platform in {"reddit", "xiaohongshu", "perplexity"}:
                session_path.mkdir(parents=True, exist_ok=True)
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(session_path),
                    channel="chrome",
                    headless=False,
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(login_url)

                print(
                    f"Login to {platform} ({resolved_purpose or 'default'}) "
                    f"for account {account.handle}, "
                    "then press Enter here."
                )
                input()

                context.close()
            else:
                browser = playwright.chromium.launch(
                    channel="chrome",
                    headless=False,
                )
                context = browser.new_context()
                page = context.new_page()
                page.goto(login_url)

                print(
                    f"Login to {platform} ({resolved_purpose or 'default'}) "
                    f"for account {account.handle}, "
                    "then press Enter here."
                )
                input()

                context.storage_state(path=str(session_path))
                browser.close()

        now = self._now()
        if resolved_purpose == "creator":
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
            if path.is_dir():
                shutil.rmtree(path)
            else:
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
    def default_purpose(
        platform: str,
        purpose: str | None = None,
    ) -> str | None:
        if platform == "xiaohongshu":
            return purpose or "creator"

        return None

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
        return slug.strip("-") or "account"
