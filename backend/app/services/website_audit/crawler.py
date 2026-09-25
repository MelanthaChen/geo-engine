from dataclasses import dataclass
import re
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
    content_type: str | None = None
    html_accepted: bool = False


@dataclass
class CrawlCoverage:
    inventory_source: str
    crawl_limit: int
    sample_page_limit: int
    discovered_urls: int
    selected_urls: int
    not_selected_due_to_sampling: int
    requested_urls: int
    successful_responses: int
    accepted_html_responses: int
    skipped_due_to_limit: int
    robots_txt_detected: bool = False
    sitemap_url_count: int = 0

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
    sample_pages: int = 30,
    timeout_seconds: int = 8,
) -> CrawlResult:
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if sample_pages < 1:
        raise ValueError("sample_pages must be at least 1")

    base_url = normalize_base_url(domain)
    host = (urlparse(base_url).hostname or "").lower()
    sitemap_discovery = discover_sitemap(
        base_url=base_url,
        host=host,
        timeout_seconds=timeout_seconds,
    )
    sitemap_urls = sitemap_discovery.urls
    inventory_source = "sitemap" if sitemap_urls else "recursive_links"
    audited_url = normalize_url(base_url)
    homepage_url = origin_homepage(audited_url)
    discovered = set(deduplicate([audited_url, *sitemap_urls]))
    homepage_links: set[str] = set()
    seen: set[str] = set()
    responses: list[CrawlResponse] = []
    selection_limit = min(sample_pages, max_pages)

    def request_selected(url: str) -> None:
        if url in seen or len(responses) >= selection_limit:
            return
        seen.add(url)
        response = fetch_page(url=url, timeout_seconds=timeout_seconds)
        responses.append(response)

        if not response.html or not is_html_success(response.status_code):
            return
        links = extract_internal_links(
            html=response.html,
            current_url=response.url,
            host=host,
        )
        discovered.update(links)
        if url == homepage_url:
            homepage_links.update(links)

    request_selected(audited_url)
    if homepage_url in discovered:
        request_selected(homepage_url)

    if sitemap_urls:
        selected = select_representative_urls(
            urls=discovered,
            audited_url=audited_url,
            homepage_url=homepage_url,
            homepage_links=homepage_links,
            limit=selection_limit,
        )
        for url in selected:
            request_selected(url)
    else:
        while len(responses) < selection_limit:
            selected = select_representative_urls(
                urls=discovered,
                audited_url=audited_url,
                homepage_url=homepage_url,
                homepage_links=homepage_links,
                limit=selection_limit,
            )
            next_url = next((url for url in selected if url not in seen), None)
            if next_url is None:
                break
            request_selected(next_url)

    selected_count = len(responses)
    sampling_excluded = max(len(discovered) - sample_pages, 0)
    hard_limit_skipped = max(min(len(discovered), sample_pages) - max_pages, 0)

    successful = sum(is_html_success(response.status_code) for response in responses)
    accepted_html = sum(response.html_accepted for response in responses)
    return CrawlResult(
        responses=responses,
        coverage=CrawlCoverage(
            inventory_source=inventory_source,
            crawl_limit=max_pages,
            sample_page_limit=sample_pages,
            discovered_urls=len(discovered),
            selected_urls=selected_count,
            not_selected_due_to_sampling=sampling_excluded,
            requested_urls=len(responses),
            successful_responses=successful,
            accepted_html_responses=accepted_html,
            robots_txt_detected=sitemap_discovery.robots_txt_detected,
            sitemap_url_count=len(sitemap_urls),
            skipped_due_to_limit=hard_limit_skipped,
        ),
    )


HIGH_LEVEL_SEGMENTS = {
    "about", "company", "contact", "docs", "documentation", "examples",
    "faq", "features", "guide", "guides", "help", "learn", "pricing",
    "research", "resources", "security", "support",
}


def select_representative_urls(
    *,
    urls: set[str] | list[str],
    audited_url: str,
    homepage_url: str,
    homepage_links: set[str] | list[str],
    limit: int,
) -> list[str]:
    """Select a stable, structurally diverse subset from discovered URLs."""
    if limit < 1:
        return []
    inventory = set(urls)
    homepage_link_set = set(homepage_links) & inventory
    selected: list[str] = []

    add_if_present(selected, inventory, audited_url, limit)
    add_if_present(selected, inventory, homepage_url, limit)

    homepage_candidates = homepage_link_set - set(selected)
    selected.extend(round_robin_families(
        homepage_candidates,
        limit=limit - len(selected),
    ))

    remaining = inventory - set(selected)
    selected.extend(round_robin_families(
        remaining,
        limit=limit - len(selected),
    ))
    return selected[:limit]


def round_robin_families(urls: set[str], *, limit: int) -> list[str]:
    if limit <= 0:
        return []
    families: dict[str, list[str]] = {}
    for url in urls:
        families.setdefault(path_family(url), []).append(url)
    for members in families.values():
        members.sort(key=url_priority)

    family_order = sorted(
        families,
        key=lambda family: (url_priority(families[family][0]), family),
    )
    selected: list[str] = []
    while len(selected) < limit:
        added = False
        for family in family_order:
            if families[family] and len(selected) < limit:
                selected.append(families[family].pop(0))
                added = True
        if not added:
            break
    return selected


def path_family(url: str) -> str:
    segments = path_segments(url)
    if not segments:
        return "/"
    index = 1 if len(segments) > 1 and is_locale_segment(segments[0]) else 0
    return f"/{segments[index].lower()}"


def url_priority(url: str) -> tuple[int, int, str]:
    segments = path_segments(url)
    informational = any(segment.lower() in HIGH_LEVEL_SEGMENTS for segment in segments)
    return (len(segments), 0 if informational else 1, url)


def path_segments(url: str) -> list[str]:
    return [segment for segment in urlparse(url).path.split("/") if segment]


def is_locale_segment(segment: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z]{2}(?:-[a-zA-Z]{2})?", segment))


def origin_homepage(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))


def add_if_present(
    selected: list[str],
    inventory: set[str],
    url: str,
    limit: int,
) -> None:
    if len(selected) < limit and url in inventory and url not in selected:
        selected.append(url)


def discover_sitemap_urls(
    *,
    base_url: str,
    host: str,
    timeout_seconds: int,
) -> list[str]:
    return discover_sitemap(
        base_url=base_url,
        host=host,
        timeout_seconds=timeout_seconds,
    ).urls


@dataclass
class SitemapDiscovery:
    urls: list[str]
    robots_txt_detected: bool


def discover_sitemap(
    *,
    base_url: str,
    host: str,
    timeout_seconds: int,
) -> SitemapDiscovery:
    sitemap_locations = []
    robots_text = fetch_text(urljoin(base_url, "/robots.txt"), timeout_seconds)
    if robots_text:
        sitemap_locations.extend(parse_robots_sitemaps(robots_text, base_url, host))
    sitemap_locations.append(normalize_url(urljoin(base_url, "/sitemap.xml")))

    page_urls: list[str] = []
    seen_pages: set[str] = set()
    visited_sitemaps: set[str] = set()
    for sitemap_url in deduplicate(sitemap_locations):
        resolve_sitemap_document(
            sitemap_url=sitemap_url,
            base_url=base_url,
            host=host,
            timeout_seconds=timeout_seconds,
            visited_sitemaps=visited_sitemaps,
            seen_pages=seen_pages,
            page_urls=page_urls,
        )
    return SitemapDiscovery(
        urls=page_urls,
        robots_txt_detected=bool(robots_text.strip()),
    )


def resolve_sitemap_document(
    *,
    sitemap_url: str,
    base_url: str,
    host: str,
    timeout_seconds: int,
    visited_sitemaps: set[str],
    seen_pages: set[str],
    page_urls: list[str],
) -> None:
    sitemap_url = normalize_url(sitemap_url)
    if sitemap_url in visited_sitemaps or not same_host(sitemap_url, host):
        return
    visited_sitemaps.add(sitemap_url)

    xml = fetch_text(sitemap_url, timeout_seconds)
    if not xml:
        return
    kind, locations = parse_sitemap_document(xml, base_url, host)
    if kind is None:
        return

    for location in locations:
        if kind == "sitemapindex" or looks_like_sitemap(location):
            resolve_sitemap_document(
                sitemap_url=location,
                base_url=base_url,
                host=host,
                timeout_seconds=timeout_seconds,
                visited_sitemaps=visited_sitemaps,
                seen_pages=seen_pages,
                page_urls=page_urls,
            )
        elif location not in seen_pages:
            seen_pages.add(location)
            page_urls.append(location)


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


def parse_sitemap_document(
    xml: str,
    base_url: str,
    host: str,
) -> tuple[str | None, list[str]]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return None, []
    kind = local_name(root.tag)
    if kind not in {"urlset", "sitemapindex"}:
        return None, []

    urls = []
    for element in root.iter():
        if local_name(element.tag) != "loc" or not element.text:
            continue
        url = normalize_url(urljoin(base_url, element.text.strip()))
        if same_host(url, host):
            urls.append(url)
    return kind, deduplicate(urls)


def parse_sitemap_urlset(xml: str, base_url: str, host: str) -> list[str]:
    kind, urls = parse_sitemap_document(xml, base_url, host)
    return urls if kind == "urlset" else []


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
        html_accepted = is_html_success(response.status_code) and "html" in content_type.lower()
        html = response.text if html_accepted else ""

        return CrawlResponse(
            url=normalize_url(response.url),
            status_code=response.status_code,
            html=html,
            content_type=content_type,
            html_accepted=html_accepted,
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


def looks_like_sitemap(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".xml")
