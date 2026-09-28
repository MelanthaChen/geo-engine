"""Exa Search API retrieval for controlled GEO source sets."""

from datetime import datetime, timezone
import hashlib
import logging

import requests

from app.core.config import settings
from app.ge.search_provider import RetrievedDocument, SearchProviderError
from app.services.website_audit.crawler import fetch_page
from app.services.website_audit.extractor import extract_page


logger = logging.getLogger(__name__)


class ExaRetrievalError(SearchProviderError):
    pass


class ExaSearchProvider:
    """Normalize ordered Exa results and hydrate real source-page snapshots."""

    endpoint = "https://api.exa.ai/search"
    provider_id = "exa"
    display_name = "Exa"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        result_count: int | None = None,
        timeout_seconds: int = 15,
    ):
        self.api_key = api_key if api_key is not None else settings.EXA_API_KEY
        self.result_count = result_count or settings.EXA_SEARCH_RESULT_COUNT
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        if not self.api_key:
            raise ExaRetrievalError("Exa Search API is not configured.")

        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                },
                json={
                    "query": query,
                    "numResults": self.result_count,
                    "type": "auto",
                },
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ExaRetrievalError("Exa Search request timed out.") from exc
        except requests.RequestException as exc:
            raise ExaRetrievalError(f"Exa Search request failed: {exc}") from exc

        if response.status_code in {401, 403}:
            raise ExaRetrievalError(
                "Exa Search authentication failed. Check EXA_API_KEY."
            )
        if response.status_code == 429:
            raise ExaRetrievalError(
                "Exa Search rate limit was exceeded. Try again later."
            )
        if 500 <= response.status_code < 600:
            raise ExaRetrievalError(
                f"Exa Search is temporarily unavailable (HTTP {response.status_code})."
            )
        if not 200 <= response.status_code < 300:
            raise ExaRetrievalError(
                f"Exa Search request failed with HTTP status {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExaRetrievalError(
                "Exa Search returned an invalid JSON response."
            ) from exc

        rows = []
        request_id = payload.get("requestId")
        for rank, item in enumerate(payload.get("results") or [], start=1):
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            rows.append({
                "rank": rank,
                "title": str(item.get("title") or url).strip(),
                "url": url,
                "snippet": self._preview(item),
                "provider_metadata": {
                    "request_id": request_id,
                    "id": item.get("id"),
                    "published_date": item.get("publishedDate"),
                    "author": item.get("author"),
                },
            })
        if not rows:
            raise ExaRetrievalError("Exa Search returned no web results for this query.")

        retrieved_at = datetime.now(timezone.utc)
        documents = []
        for row in rows[: self.result_count]:
            page = extract_page(
                fetch_page(row["url"], timeout_seconds=self.timeout_seconds)
            )
            plain_text = (
                page.body_text
                if page.status_code and 200 <= page.status_code < 300
                else ""
            )
            if not plain_text:
                logger.warning(
                    "[EXA RETRIEVAL] Page content unavailable rank=%s url=%s",
                    row["rank"],
                    row["url"],
                )
            documents.append(
                RetrievedDocument(
                    rank=row["rank"],
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
                    provider_metadata=row["provider_metadata"],
                )
            )
        return documents[:top_k]

    @staticmethod
    def _preview(item: dict) -> str:
        highlights = item.get("highlights") or []
        if highlights:
            return str(highlights[0]).strip()
        return str(item.get("text") or "").strip()
