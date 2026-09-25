from dataclasses import dataclass, field

import pytest

from app.services.website_audit import crawler
from app.services.website_audit.crawler import CrawlResponse
from app.services.website_audit.extractor import extract_pages


@dataclass
class FakeResponse:
    url: str
    text: str
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=lambda: {"content-type": "text/html"})


def install_responses(monkeypatch, responses):
    requested = []

    def fake_get(url, **_kwargs):
        requested.append(url)
        response = responses.get(url)
        if response is None:
            return FakeResponse(url=url, text="", status_code=404)
        return response

    monkeypatch.setattr(crawler.requests, "get", fake_get)
    return requested


def sitemap(*urls):
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'


def test_sitemap_is_primary_inventory_and_filters_external_hosts(monkeypatch):
    base = "https://example.com"
    responses = {
        f"{base}/robots.txt": FakeResponse(f"{base}/robots.txt", ""),
        f"{base}/sitemap.xml": FakeResponse(
            f"{base}/sitemap.xml",
            sitemap(f"{base}/", f"{base}/guide", "https://outside.example/page", f"{base}/guide/"),
            headers={"content-type": "application/xml"},
        ),
        f"{base}/": FakeResponse(f"{base}/", "<html><body>Home</body></html>"),
        f"{base}/guide": FakeResponse(f"{base}/guide", "<html><body>Guide</body></html>"),
    }
    install_responses(monkeypatch, responses)

    result = crawler.crawl_website(base, max_pages=10)

    assert result.coverage.inventory_source == "sitemap"
    assert result.coverage.discovered_urls == 2
    assert [response.url for response in result.responses] == [f"{base}/", f"{base}/guide"]


def test_robots_declared_sitemap_is_discovered(monkeypatch):
    base = "https://example.com"
    custom = f"{base}/site-index.xml"
    responses = {
        f"{base}/robots.txt": FakeResponse(f"{base}/robots.txt", f"User-agent: *\nSitemap: {custom}"),
        custom: FakeResponse(custom, sitemap(f"{base}/from-robots"), headers={"content-type": "application/xml"}),
        f"{base}/sitemap.xml": FakeResponse(f"{base}/sitemap.xml", "", status_code=404),
        f"{base}/from-robots": FakeResponse(f"{base}/from-robots", "<html><body>Found</body></html>"),
    }
    requested = install_responses(monkeypatch, responses)

    result = crawler.crawl_website(base, max_pages=10)

    assert custom in requested
    assert result.coverage.inventory_source == "sitemap"
    assert result.responses[0].url == f"{base}/from-robots"


def test_crawl_limit_reports_truncation(monkeypatch):
    base = "https://example.com"
    urls = [f"{base}/{number}" for number in range(5)]
    responses = {
        f"{base}/robots.txt": FakeResponse(f"{base}/robots.txt", ""),
        f"{base}/sitemap.xml": FakeResponse(f"{base}/sitemap.xml", sitemap(*urls), headers={"content-type": "application/xml"}),
        **{url: FakeResponse(url, f"<html><body>Page {index}</body></html>") for index, url in enumerate(urls)},
    }
    install_responses(monkeypatch, responses)

    result = crawler.crawl_website(base, max_pages=2)

    assert result.coverage.discovered_urls == 5
    assert result.coverage.requested_urls == 2
    assert result.coverage.skipped_due_to_limit == 3
    assert result.coverage.truncated is True


def test_site_without_sitemap_recursively_follows_internal_links(monkeypatch):
    base = "https://example.com"
    responses = {
        f"{base}/robots.txt": FakeResponse(f"{base}/robots.txt", ""),
        f"{base}/sitemap.xml": FakeResponse(f"{base}/sitemap.xml", "", status_code=404),
        f"{base}/": FakeResponse(f"{base}/", '<html><body><a href="/child">Child</a></body></html>'),
        f"{base}/child": FakeResponse(f"{base}/child", '<html><body><a href="/grandchild">Grandchild</a><a href="/">Home</a></body></html>'),
        f"{base}/grandchild": FakeResponse(f"{base}/grandchild", "<html><body>End</body></html>"),
    }
    install_responses(monkeypatch, responses)

    result = crawler.crawl_website(base, max_pages=10)

    assert result.coverage.inventory_source == "recursive_links"
    assert result.coverage.discovered_urls == 3
    assert result.coverage.requested_urls == 3
    assert result.coverage.skipped_due_to_limit == 0


def test_duplicate_content_is_hashed_and_excluded_from_unique_evidence():
    html = "<html><body><h1>Same page</h1><p>Identical content.</p></body></html>"
    pages = extract_pages([
        CrawlResponse("https://example.com/", 200, html),
        CrawlResponse("https://example.com/missing", 200, html),
    ])

    assert pages[0].content_sha256 == pages[1].content_sha256
    assert pages[0].is_duplicate is False
    assert pages[1].is_duplicate is True
    assert pages[1].duplicate_of_url == "https://example.com/"


def test_spa_soft_fallback_urls_remain_provenance_but_not_independent_content():
    html = "<html><body><main>SPA shell with prerendered content</main></body></html>"
    pages = extract_pages([
        CrawlResponse("https://example.com/", 200, html),
        CrawlResponse("https://example.com/not-a-real-route", 200, html),
        CrawlResponse("https://example.com/also-missing", 200, html),
    ])

    assert len(pages) == 3
    assert sum(not page.is_duplicate for page in pages) == 1
    assert sum(page.is_duplicate for page in pages) == 2


def test_crawl_limit_must_be_explicit_and_positive():
    with pytest.raises(ValueError, match="max_pages"):
        crawler.crawl_website("https://example.com", max_pages=0)
