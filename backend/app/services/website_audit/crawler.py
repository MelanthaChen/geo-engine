from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup


@dataclass
class CrawlResponse:
    url: str
    status_code: int | None
    html: str
    error: str | None = None


@dataclass
class CrawlCoverage:
    inventory_source: str
    crawl_limit: int
    discovered_urls: int
    requested_urls: int
    successful_responses: int
    skipped_due_to_limit: int

    @property
    def truncated(self) -> bool:
        return self.skipped_due_to_limit > 0


@dataclass
class CrawlResult:
    responses: list[CrawlResponse]
    coverage: CrawlCoverage


def crawl_website(
    domain: str,
    *,
    max_pages: int,
    timeout_seconds: int = 8,
) -> CrawlResult:
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    base_url = normalize_base_url(domain)
    host = (urlparse(base_url).hostname or "").lower()
    sitemap_urls = discover_sitemap_urls(
        base_url=base_url,
        host=host,
        timeout_seconds=timeout_seconds,
    )
    inventory_source = "sitemap" if sitemap_urls else "recursive_links"
    pending = list(sitemap_urls or [normalize_url(base_url)])
    discovered = set(pending)
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
            if link not in discovered:
                discovered.add(link)
                pending.append(link)

    successful = sum(is_html_success(response.status_code) for response in responses)
    return CrawlResult(
        responses=responses,
        coverage=CrawlCoverage(
            inventory_source=inventory_source,
            crawl_limit=max_pages,
            discovered_urls=len(discovered),
            requested_urls=len(responses),
            successful_responses=successful,
            skipped_due_to_limit=len(discovered - seen),
        ),
    )


def discover_sitemap_urls(
    *,
    base_url: str,
    host: str,
    timeout_seconds: int,
) -> list[str]:
    sitemap_locations = []
    robots_text = fetch_text(urljoin(base_url, "/robots.txt"), timeout_seconds)
    if robots_text:
        sitemap_locations.extend(parse_robots_sitemaps(robots_text, base_url, host))
    sitemap_locations.append(normalize_url(urljoin(base_url, "/sitemap.xml")))

    urls: list[str] = []
    seen: set[str] = set()
    for sitemap_url in deduplicate(sitemap_locations):
        xml = fetch_text(sitemap_url, timeout_seconds)
        if not xml:
            continue
        for url in parse_sitemap_urlset(xml, base_url, host):
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def fetch_text(url: str, timeout_seconds: int) -> str:
    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={"User-Agent": "GEOEngineAuditBot/1.0 (website audit; contact site owner)"},
            allow_redirects=True,
        )
        if not is_html_success(response.status_code):
            return ""
        return response.text
    except requests.RequestException:
        return ""


def parse_robots_sitemaps(text: str, base_url: str, host: str) -> list[str]:
    locations = []
    for line in text.splitlines():
        name, separator, value = line.partition(":")
        if not separator or name.strip().lower() != "sitemap":
            continue
        location = normalize_url(urljoin(base_url, value.strip()))
        if same_host(location, host):
            locations.append(location)
    return locations


def parse_sitemap_urlset(xml: str, base_url: str, host: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []
    if local_name(root.tag) != "urlset":
        return []

    urls = []
    for element in root.iter():
        if local_name(element.tag) != "loc" or not element.text:
            continue
        url = normalize_url(urljoin(base_url, element.text.strip()))
        if same_host(url, host):
            urls.append(url)
    return deduplicate(urls)


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
    hostname = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{hostname}{port}"

    return urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
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

        if not same_host(absolute_url, host):
            continue

        if looks_like_asset(urlparse(absolute_url).path):
            continue

        links.append(absolute_url)

    return deduplicate(links)


def same_host(url: str, host: str) -> bool:
    return (urlparse(url).hostname or "").lower() == host.lower()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


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
