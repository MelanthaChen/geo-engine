from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.ge.document_cleaner import DocumentCleaner
from app.ge.search_provider import RetrievedDocument


class GoogleSearchProvider:
    def __init__(self, cleaner: DocumentCleaner | None = None):
        self.cleaner = cleaner or DocumentCleaner()

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_ENGINE_ID:
            return self._search_custom_api(query=query, top_k=top_k)

        return self._search_google_html(query=query, top_k=top_k)

    def _search_custom_api(
        self,
        query: str,
        top_k: int,
    ) -> list[RetrievedDocument]:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": settings.GOOGLE_SEARCH_API_KEY,
                "cx": settings.GOOGLE_SEARCH_ENGINE_ID,
                "q": query,
                "num": min(top_k, 10),
            },
            timeout=15,
        )
        response.raise_for_status()
        items = response.json().get("items", [])

        return self._hydrate_results(
            [
                {
                    "title": item.get("title") or item.get("link") or "",
                    "url": item.get("link") or "",
                    "snippet": item.get("snippet") or "",
                }
                for item in items[:top_k]
            ],
            top_k=top_k,
        )

    def _search_google_html(
        self,
        query: str,
        top_k: int,
    ) -> list[RetrievedDocument]:
        response = requests.get(
            f"https://www.google.com/search?q={quote_plus(query)}&num={top_k}",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            },
            timeout=15,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        rows = []

        for anchor in soup.select("a"):
            href = anchor.get("href") or ""
            title = anchor.get_text(" ", strip=True)

            if not href.startswith("/url?q=") or not title:
                continue

            url = href.split("/url?q=", 1)[1].split("&", 1)[0]

            if not self._is_http_url(url):
                continue

            rows.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": title,
                }
            )

            if len(rows) >= top_k:
                break

        return self._hydrate_results(rows, top_k=top_k)

    def _hydrate_results(
        self,
        rows: list[dict[str, str]],
        top_k: int,
    ) -> list[RetrievedDocument]:
        documents = []

        for index, row in enumerate(rows[:top_k], start=1):
            plain_text = self._fetch_plain_text(
                url=row["url"],
                fallback=row.get("snippet") or row["title"],
            )
            documents.append(
                RetrievedDocument(
                    rank=index,
                    title=row["title"],
                    url=row["url"],
                    plain_text=plain_text,
                )
            )

        return documents

    def _fetch_plain_text(self, url: str, fallback: str) -> str:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "GEO Engine Experiment Lab/1.0"},
                timeout=12,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                return self.cleaner.clean_html(response.text)

            if "text/" in content_type or not content_type:
                return self.cleaner.clean_text(response.text)
        except requests.RequestException:
            pass

        return self.cleaner.clean_text(fallback)

    def _is_http_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
