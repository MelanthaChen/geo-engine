from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.account import Account


class RetrievalError(RuntimeError):
    """Raised when a platform retriever cannot return real platform data."""


@dataclass
class RetrievedPlatformQuestion:
    platform: str
    title: str
    body: str | None = None
    url: str | None = None
    author: str | None = None
    hashtags: list[str] | None = None
    score: int | None = None
    engagement_metrics: dict | None = None
    created_at: datetime | None = None
    retrieval_method: str | None = None
    raw_metadata: dict | None = None


class PlatformRetriever(Protocol):
    platform: str

    def search(
        self,
        query: str,
        limit: int,
        *,
        db: Session | None = None,
        property_id: int | None = None,
        account: Account | None = None,
    ) -> list[RetrievedPlatformQuestion]:
        ...

    def fetch_post(
        self,
        url: str,
        *,
        account: Account | None = None,
    ) -> RetrievedPlatformQuestion:
        ...

    def fetch_comments(
        self,
        url: str,
        *,
        account: Account | None = None,
    ) -> list[dict]:
        ...
