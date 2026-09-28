"""Brave Web Search retrieval for controlled GEO source sets."""

from datetime import datetime, timezone
import hashlib
import logging

import requests

from app.core.config import settings
from app.ge.search_provider import RetrievedDocument, SearchProviderError
from app.services.website_audit.crawler import fetch_page
from app.services.website_audit.extractor import extract_page


logger = logging.getLogger(__name__)


class BraveRetrievalError(SearchProviderError):
    pass


class BraveSearchProvider:
    """Retrieve ordered web results and hydrate them with real page content."""

    endpoint = "https://api.search.brave.com/res/v1/web/search"
    provider_id = "brave"
    display_name = "Brave Search"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        result_count: int | None = None,
        timeout_seconds: int = 15,
    ):
        self.api_key = api_key if api_key is not None else settings.BRAVE_SEARCH_API_KEY
        self.result_count = result_count or settings.BRAVE_SEARCH_RESULT_COUNT
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        if not self.api_key:
            raise BraveRetrievalError("Brave Search API is not configured.")

        count = min(20, self.result_count)
        try:
            response = requests.get(
                self.endpoint,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key,
                },
                params={
                    "q": query,
                    "count": count,
                    "country": "US",
                    "search_lang": "en",
                },
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise BraveRetrievalError(
                f"Brave Search request failed: {exc}"
            ) from exc

        if response.status_code in {401, 403}:
            raise BraveRetrievalError(
                "Brave Search authentication failed. Check BRAVE_SEARCH_API_KEY."
            )
        if response.status_code == 429:
            raise BraveRetrievalError(
                "Brave Search rate limit was exceeded. Try again later."
            )
        if 500 <= response.status_code < 600:
            raise BraveRetrievalError(
                f"Brave Search is temporarily unavailable (HTTP {response.status_code})."
            )
        if not 200 <= response.status_code < 300:
            raise BraveRetrievalError(
                f"Brave Search request failed with HTTP status {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise BraveRetrievalError(
                "Brave Search returned an invalid JSON response."
            ) from exc

        results = (payload.get("web") or {}).get("results") or []
        rows = [
            {
                "rank": rank,
                "title": str(item.get("title") or item.get("url") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "snippet": str(item.get("description") or "").strip(),
            }
            for rank, item in enumerate(results, start=1)
            if str(item.get("url") or "").strip()
        ]
        if not rows:
            raise BraveRetrievalError(
                "Brave Search returned no web results for this query."
            )

        retrieved_at = datetime.now(timezone.utc)
        documents = []
        for row in rows[:count]:
            rank = row["rank"]
            page = extract_page(
                fetch_page(row["url"], timeout_seconds=self.timeout_seconds)
            )
            plain_text = page.body_text if page.status_code and 200 <= page.status_code < 300 else ""
            if not plain_text:
                logger.warning(
                    "[BRAVE RETRIEVAL] Page content unavailable rank=%s url=%s",
                    rank,
                    row["url"],
                )
            documents.append(
                RetrievedDocument(
                    rank=rank,
                    title=row["title"],
                    url=row["url"],
                    plain_text=plain_text,
                    snippet=row["snippet"],
                    retrieval_provider=self.provider_id,
                    retrieved_at=retrieved_at,
                    content_sha256=(
                        page.content_sha256
                        or (
                            hashlib.sha256(plain_text.encode("utf-8")).hexdigest()
                            if plain_text else None
                        )
                    ),
                )
            )
        return documents[:top_k]
