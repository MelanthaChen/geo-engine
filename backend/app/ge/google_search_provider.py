import logging
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.ge.document_cleaner import DocumentCleaner
from app.ge.search_provider import RetrievedDocument


logger = logging.getLogger(__name__)


class GoogleRetrievalError(RuntimeError):
    pass


class GoogleSearchProvider:
    def __init__(self, cleaner: DocumentCleaner | None = None):
        self.cleaner = cleaner or DocumentCleaner()

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        logger.info(
            "[GOOGLE RETRIEVAL] Search requested query=%r top_k=%s",
            query,
            top_k,
        )

        if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_ENGINE_ID:
            logger.info("[GOOGLE RETRIEVAL] Backend=Google Custom Search API")
            return self._search_custom_api(query=query, top_k=top_k)

        logger.warning(
            "[GOOGLE RETRIEVAL] Google API credentials missing; "
            "GOOGLE_SEARCH_API_KEY=%s GOOGLE_SEARCH_ENGINE_ID=%s. "
            "Backend=Google HTML fallback",
            "set" if settings.GOOGLE_SEARCH_API_KEY else "missing",
            "set" if settings.GOOGLE_SEARCH_ENGINE_ID else "missing",
        )
        return self._search_google_html(query=query, top_k=top_k)

    def _search_custom_api(
        self,
        query: str,
        top_k: int,
    ) -> list[RetrievedDocument]:
        try:
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
        except requests.RequestException as exc:
            logger.exception(
                "[GOOGLE RETRIEVAL] Google API request failed query=%r",
                query,
            )
            raise GoogleRetrievalError(
                "Google API retrieval failed during HTTP request: "
                f"{exc}"
            ) from exc

        logger.info(
            "[GOOGLE RETRIEVAL] Google API status=%s response_length=%s",
            response.status_code,
            len(response.text or ""),
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.exception(
                "[GOOGLE RETRIEVAL] Google API returned non-2xx status "
                "query=%r status=%s body_preview=%r",
                query,
                response.status_code,
                response.text[:500],
            )
            raise GoogleRetrievalError(
                "Google API retrieval failed with HTTP status "
                f"{response.status_code}. Body preview: {response.text[:300]}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            logger.exception(
                "[GOOGLE RETRIEVAL] Google API response was not JSON "
                "query=%r body_preview=%r",
                query,
                response.text[:500],
            )
            raise GoogleRetrievalError(
                "Google API retrieval failed because the response was not JSON."
            ) from exc

        items = payload.get("items", [])
        logger.info(
            "[GOOGLE RETRIEVAL] Google API parsed_results=%s",
            len(items),
        )

        rows = [
            {
                "title": item.get("title") or item.get("link") or "",
                "url": item.get("link") or "",
                "snippet": item.get("snippet") or "",
            }
            for item in items[:top_k]
        ]
        self._log_parsed_urls(rows)

        if not rows:
            raise GoogleRetrievalError(
                "Google API retrieval returned zero search results. "
                "Check GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID, quota, "
                "and whether the Custom Search Engine can search the web."
            )

        return self._hydrate_results(
            rows,
            top_k=top_k,
            backend_name="Google API",
        )

    def _search_google_html(
        self,
        query: str,
        top_k: int,
    ) -> list[RetrievedDocument]:
        search_url = (
            f"https://www.google.com/search?q={quote_plus(query)}&num={top_k}"
        )

        try:
            response = requests.get(
                search_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    )
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            logger.exception(
                "[GOOGLE RETRIEVAL] HTML fallback HTTP request failed "
                "query=%r url=%s",
                query,
                search_url,
            )
            raise GoogleRetrievalError(
                "Google HTML fallback failed during HTTP request: "
                f"{exc}"
            ) from exc

        logger.info(
            "[GOOGLE RETRIEVAL] HTML fallback status=%s response_length=%s",
            response.status_code,
            len(response.text or ""),
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.exception(
                "[GOOGLE RETRIEVAL] HTML fallback returned non-2xx status "
                "query=%r status=%s body_preview=%r",
                query,
                response.status_code,
                response.text[:500],
            )
            raise GoogleRetrievalError(
                "Google HTML fallback failed with HTTP status "
                f"{response.status_code}. Body preview: {response.text[:300]}"
            ) from exc

        soup = BeautifulSoup(response.text, "html.parser")
        rows = []
        anchors = soup.select("a")
        candidate_anchor_count = 0

        for anchor in anchors:
            href = anchor.get("href") or ""
            title = anchor.get_text(" ", strip=True)

            if not href.startswith("/url?q=") or not title:
                continue

            candidate_anchor_count += 1
            url = href.split("/url?q=", 1)[1].split("&", 1)[0]

            if not self._is_http_url(url):
                logger.debug(
                    "[GOOGLE RETRIEVAL] HTML fallback skipped non-http URL=%r",
                    url,
                )
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

        logger.info(
            "[GOOGLE RETRIEVAL] HTML fallback anchors=%s candidate_anchors=%s "
            "parsed_results=%s",
            len(anchors),
            candidate_anchor_count,
            len(rows),
        )
        self._log_parsed_urls(rows)

        if not rows:
            reason = self._html_parse_failure_reason(
                response_text=response.text,
                anchors=anchors,
                candidate_anchor_count=candidate_anchor_count,
            )
            logger.error(
                "[GOOGLE RETRIEVAL] HTML fallback parsed zero results. "
                "reason=%s body_preview=%r sample_hrefs=%s",
                reason,
                response.text[:500],
                [
                    anchor.get("href")
                    for anchor in anchors[:10]
                ],
            )
            raise GoogleRetrievalError(
                "Google HTML fallback parsed zero search results. "
                f"Reason: {reason}. "
                "Configure GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID "
                "for reliable retrieval."
            )

        return self._hydrate_results(
            rows,
            top_k=top_k,
            backend_name="Google HTML fallback",
        )

    def _hydrate_results(
        self,
        rows: list[dict[str, str]],
        top_k: int,
        backend_name: str,
    ) -> list[RetrievedDocument]:
        documents = []

        for index, row in enumerate(rows[:top_k], start=1):
            plain_text, download_succeeded = self._fetch_plain_text(
                url=row["url"],
                fallback=row.get("snippet") or row["title"],
            )
            logger.info(
                "[GOOGLE RETRIEVAL] Document rank=%s url=%s "
                "download_succeeded=%s cleaned_length=%s",
                index,
                row["url"],
                download_succeeded,
                len(plain_text),
            )
            documents.append(
                RetrievedDocument(
                    rank=index,
                    title=row["title"],
                    url=row["url"],
                    plain_text=plain_text,
                )
            )

        if not documents:
            raise GoogleRetrievalError(
                f"{backend_name} parsed search results but hydrated zero "
                "documents."
            )

        return documents

    def _fetch_plain_text(self, url: str, fallback: str) -> tuple[str, bool]:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "GEO Engine Experiment Lab/1.0"},
                timeout=12,
            )
            logger.info(
                "[GOOGLE RETRIEVAL] Document download url=%s status=%s "
                "response_length=%s",
                url,
                response.status_code,
                len(response.text or ""),
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                return self.cleaner.clean_html(response.text), True

            if "text/" in content_type or not content_type:
                return self.cleaner.clean_text(response.text), True

            logger.warning(
                "[GOOGLE RETRIEVAL] Document download unsupported "
                "content_type=%r url=%s; using search snippet fallback",
                content_type,
                url,
            )
        except requests.RequestException as exc:
            logger.warning(
                "[GOOGLE RETRIEVAL] Document download failed url=%s error=%s; "
                "using search snippet fallback",
                url,
                exc,
            )

        return self.cleaner.clean_text(fallback), False

    def _is_http_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _log_parsed_urls(self, rows: list[dict[str, str]]):
        logger.info(
            "[GOOGLE RETRIEVAL] Parsed URLs=%s",
            [row.get("url") for row in rows],
        )

    def _html_parse_failure_reason(
        self,
        response_text: str,
        anchors,
        candidate_anchor_count: int,
    ) -> str:
        lowered = response_text.lower()

        if "our systems have detected unusual traffic" in lowered:
            return "Google returned an unusual-traffic / CAPTCHA page"

        if "enable javascript" in lowered:
            return "Google returned a JavaScript-required page"

        if not anchors:
            return "response contained no anchor tags"

        if candidate_anchor_count == 0:
            return (
                "response contained anchors, but none matched the expected "
                "Google '/url?q=' result-link pattern"
            )

        return (
            "candidate result anchors were found, but none produced valid "
            "http/https result URLs"
        )
