from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


DEFAULT_SEED_PATHS = [
    "/",
    "/pricing",
    "/features",
    "/blog",
    "/faq",
    "/about",
    "/docs",
    "/templates",
    "/examples",
    "/alternatives",
    "/compare",
    "/comparison",
]


@dataclass
class CrawlResponse:
    url: str
    status_code: int | None
    html: str
    error: str | None = None


def crawl_website(
    domain: str,
    max_pages: int = 20,
    timeout_seconds: int = 8,
) -> list[CrawlResponse]:
    base_url = normalize_base_url(domain)
    host = urlparse(base_url).netloc
    pending = [normalize_url(urljoin(base_url, path)) for path in DEFAULT_SEED_PATHS]
    seen: set[str] = set()
    responses: list[CrawlResponse] = []

    while pending and len(responses) < max_pages:
        url = pending.pop(0)

        if url in seen:
            continue

        seen.add(url)
        response = fetch_page(url=url, timeout_seconds=timeout_seconds)
        responses.append(response)

        if not response.html or not is_html_success(response.status_code):
            continue

        for link in extract_internal_links(
            html=response.html,
            current_url=response.url,
            host=host,
        ):
            if link not in seen and link not in pending:
                pending.append(link)

    return responses


def fetch_page(url: str, timeout_seconds: int) -> CrawlResponse:
    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={
                "User-Agent": (
                    "GEOEngineAuditBot/1.0 "
                    "(website audit; contact site owner)"
                )
            },
            allow_redirects=True,
        )

        content_type = response.headers.get("content-type", "")
        html = response.text if "html" in content_type.lower() else ""

        return CrawlResponse(
            url=normalize_url(response.url),
            status_code=response.status_code,
            html=html,
        )
    except requests.RequestException as error:
        return CrawlResponse(
            url=url,
            status_code=None,
            html="",
            error=str(error),
        )


def normalize_base_url(domain: str) -> str:
    value = domain.strip()

    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"

    parsed = urlparse(value)
    path = parsed.path if parsed.path and parsed.path != "/" else ""

    return urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc or parsed.path,
            path,
            "",
            "",
            "",
        )
    ).rstrip("/") + "/"


def normalize_url(url: str) -> str:
    parsed = urlparse(url)

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/") or "/",
            "",
            "",
            "",
        )
    )


def is_html_success(status_code: int | None) -> bool:
    return status_code is not None and 200 <= status_code < 300


def extract_internal_links(html: str, current_url: str, host: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()

        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute_url = normalize_url(urljoin(current_url, href))
        parsed = urlparse(absolute_url)

        if parsed.netloc != host:
            continue

        if looks_like_asset(parsed.path):
            continue

        links.append(absolute_url)

    return links


def looks_like_asset(path: str) -> bool:
    lowered = path.lower()

    return lowered.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".webp",
            ".pdf",
            ".zip",
            ".css",
            ".js",
        )
    )
