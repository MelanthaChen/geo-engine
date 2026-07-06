from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from app.services.platform_retrievers.base import (
    RetrievedPlatformQuestion,
    RetrievalError,
)
from app.services.platform_retrievers.utils import (
    clean_text,
    looks_like_question_or_discussion,
    parse_datetime,
    parse_first_integer,
)


REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = (
    "GEOEnginePlatformDiscovery/1.0 "
    "(research retrieval; contact: local-development)"
)


class RedditRetriever:
    platform = "reddit"

    def search(
        self,
        query: str,
        limit: int,
        **_,
    ) -> list[RetrievedPlatformQuestion]:
        url = (
            "https://old.reddit.com/search/"
            f"?q={quote_plus(query)}&sort=relevance&t=all"
        )

        try:
            response = requests.get(
                url,
                headers=request_headers(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise RetrievalError(f"Reddit retrieval failed: {error}") from error

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.select(".search-result")[:limit]:
            title_link = result.select_one("a.search-title")

            if not title_link:
                continue

            title = clean_text(title_link.get_text(" ", strip=True))

            if not looks_like_question_or_discussion(title):
                continue

            body_node = result.select_one(".search-expando")
            author_node = result.select_one(".search-author a")
            score_node = result.select_one(".search-score")
            timestamp_node = result.select_one("time")

            results.append(
                RetrievedPlatformQuestion(
                    platform=self.platform,
                    title=title,
                    body=clean_text(body_node.get_text(" ", strip=True))
                    if body_node
                    else None,
                    url=absolute_reddit_url(title_link.get("href")),
                    author=clean_text(author_node.get_text(" ", strip=True))
                    if author_node
                    else None,
                    score=parse_first_integer(
                        score_node.get_text(" ", strip=True)
                        if score_node
                        else ""
                    ),
                    created_at=parse_datetime(
                        timestamp_node.get("datetime")
                        if timestamp_node
                        else None
                    ),
                    retrieval_method="old_reddit_search",
                )
            )

        return results

    def fetch_post(self, url: str, **_) -> RetrievedPlatformQuestion:
        raise RetrievalError(
            "Reddit fetch_post is not implemented yet; current Reddit "
            "retrieval uses search-result snippets."
        )

    def fetch_comments(self, url: str, **_) -> list[dict]:
        raise RetrievalError(
            "Reddit fetch_comments is not implemented yet; current Reddit "
            "retrieval uses search-result snippets."
        )


def request_headers():
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    }


def absolute_reddit_url(url: str | None):
    if not url:
        return None

    if url.startswith("http"):
        return url

    return f"https://old.reddit.com{url}"
