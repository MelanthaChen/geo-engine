import asyncio

from app.services.website_audit.browser_renderer import BrowserRenderResult, run_bounded
from app.services.website_audit.crawler import CrawlResponse
from app.services.website_audit.rendering import (
    extract_audit_pages,
    needs_browser_render,
)
from app.services.website_audit.importance import select_geo_important_pages


def response(url: str, html: str) -> CrawlResponse:
    return CrawlResponse(
        url=url,
        status_code=200,
        html=html,
        content_type="text/html",
        html_accepted=True,
    )


def meaningful_html(label: str, words: int = 70) -> str:
    body = " ".join(f"{label}-{index}" for index in range(words))
    return f"<html><head><title>{label}</title></head><body><h1>{label}</h1><h2>Details</h2><p>{body}</p></body></html>"


SHELL = """
<html><head><title>Application</title></head><body><div id="root"></div>
<script>window.__APP__ = {};</script><script src="/one.js"></script>
<script src="/two.js"></script><script src="/three.js"></script></body></html>
"""


class FakeRenderer:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def render_many(self, urls, *, timeout_ms, concurrency):
        self.calls.append((urls, timeout_ms, concurrency))
        return {url: self.results[url] for url in urls}


def render_result(url: str, html: str, error: str | None = None):
    return BrowserRenderResult(url, url, 200 if not error else None, html, error)


def extract(responses, renderer=None, *, limit=10):
    return extract_audit_pages(
        responses,
        browser_enabled=True,
        browser_timeout_ms=4_000,
        browser_concurrency=2,
        browser_fallback_limit=limit,
        renderer=renderer,
    )


def test_static_ssr_and_prerendered_html_remain_http_only(monkeypatch):
    monkeypatch.setattr(
        "app.services.website_audit.rendering.BrowserRenderer",
        lambda: (_ for _ in ()).throw(AssertionError("browser runtime was initialized")),
    )
    pages = extract([
        response("https://example.test/static", meaningful_html("Static")),
        response("https://example.test/ssr", meaningful_html("SSR")),
        response("https://example.test/ssg", meaningful_html("SSG")),
    ])

    assert [page.extraction_method for page in pages] == ["http", "http", "http"]


def test_short_legitimate_http_page_does_not_trigger_on_word_count_alone():
    page = response(
        "https://example.test/contact",
        "<html><head><title>Contact</title></head><body><h1>Contact us</h1><p>Email our team today.</p></body></html>",
    )
    assert needs_browser_render(page, extract([page])[0]) == ()


def test_hydrated_page_with_meaningful_initial_html_remains_http_only():
    words = " ".join(f"server{index}" for index in range(30))
    hydrated = f"<html><head><title>Hybrid</title></head><body><div id='root'><h1>Hybrid page</h1><p>{words}</p></div><script src='hydrate.js'></script></body></html>"

    page = extract([response("https://example.test/hybrid", hydrated)])[0]

    assert page.extraction_method == "http"


def test_empty_spa_shell_uses_materially_richer_browser_dom():
    url = "https://example.test/app"
    renderer = FakeRenderer({url: render_result(url, meaningful_html("Rendered app"))})

    pages = extract([response(url, SHELL)], renderer)

    assert renderer.calls == [([url], 4_000, 2)]
    assert pages[0].extraction_method == "browser"
    assert pages[0].http_word_count == 1
    assert pages[0].browser_word_count > 70
    assert pages[0].h2_count == 1
    assert pages[0].evidence["identity"]["extraction_method"] == "browser"
    assert pages[0].evidence["headings"]["h2"] == ["Details"]
    assert pages[0].evidence["content"]["body_text"] == pages[0].body_text


def test_identical_http_shells_can_become_distinct_browser_evidence():
    urls = ["https://example.test/a", "https://example.test/b"]
    renderer = FakeRenderer({
        urls[0]: render_result(urls[0], meaningful_html("Route A")),
        urls[1]: render_result(urls[1], meaningful_html("Route B")),
    })

    pages = extract([response(url, SHELL) for url in urls], renderer)

    assert len(pages) == 2
    assert all(page.extraction_method == "browser" for page in pages)
    assert not any(page.is_duplicate for page in pages)
    assert pages[0].content_sha256 != pages[1].content_sha256


def test_equal_length_duplicate_shells_accept_route_specific_browser_content():
    urls = ["https://example.test/one", "https://example.test/two"]
    generic_words = " ".join(f"generic{index}" for index in range(55))
    shell = f"<html><head><title>App</title></head><body><div id='root'><h1>Generic route</h1><p>{generic_words}</p></div></body></html>"
    rendered = {}
    for index, url in enumerate(urls):
        route_words = " ".join(f"route{index}x{word}" for word in range(55))
        rendered[url] = render_result(url, f"<html><head><title>App</title></head><body><div id='root'><h1>Generic route</h1><p>{route_words}</p></div></body></html>")

    pages = extract([response(url, shell) for url in urls], FakeRenderer(rendered))

    assert all(page.extraction_method == "browser" for page in pages)
    assert pages[0].content_sha256 != pages[1].content_sha256


def test_lazy_loaded_partial_content_uses_richer_browser_evidence():
    url = "https://example.test/lazy"
    partial = "<html><head><title>Catalog</title></head><body><div id='app'><h1>Catalog</h1><p>Loading items</p></div><script src='1.js'></script><script src='2.js'></script><script src='3.js'></script></body></html>"
    renderer = FakeRenderer({url: render_result(url, meaningful_html("Catalog items", 90))})

    page = extract([response(url, partial)], renderer)[0]

    assert page.extraction_method == "browser"
    assert page.word_count > page.http_word_count


def test_browser_timeout_and_failure_exclude_pages_with_reasons():
    timeout_url = "https://example.test/timeout"
    failure_url = "https://example.test/failure"
    renderer = FakeRenderer({
        timeout_url: render_result(timeout_url, "", "Browser rendering timed out."),
        failure_url: render_result(failure_url, "", "Browser rendering failed: Error."),
    })

    pages = extract([response(timeout_url, SHELL), response(failure_url, SHELL)], renderer)

    assert [page.extraction_method for page in pages] == ["failed", "failed"]
    assert pages[0].word_count == 0
    assert "timed out" in pages[0].extraction_failure_reason
    assert "failed" in pages[1].extraction_failure_reason


def test_duplicate_detection_uses_final_browser_dom_and_does_not_double_count():
    urls = ["https://example.test/a", "https://example.test/b"]
    final_html = meaningful_html("Shared rendered page")
    renderer = FakeRenderer({url: render_result(url, final_html) for url in urls})

    pages = extract([response(url, SHELL) for url in urls], renderer)

    assert len(pages) == 2
    assert sum(page.is_duplicate for page in pages) == 1
    assert sum(page.word_count for page in pages if not page.is_duplicate) == pages[0].word_count


def test_fallback_only_receives_selected_responses_and_honors_total_limit():
    urls = [f"https://example.test/{index}" for index in range(3)]
    renderer = FakeRenderer({url: render_result(url, meaningful_html(str(index))) for index, url in enumerate(urls)})

    pages = extract([response(url, SHELL) for url in urls], renderer, limit=2)

    assert renderer.calls[0][0] == urls[:2]
    assert pages[2].extraction_method == "failed"
    assert "limit reached" in pages[2].extraction_failure_reason


def test_large_meaningful_shared_shell_is_verified_and_expands_to_sample_limit():
    urls = [
        f"https://example.test/{family}/route-{index}"
        for index in range(140)
        for family in (["guide", "comparison", "resources"][index % 3],)
    ]
    shared_words = " ".join(f"shared-{index}" for index in range(328))
    shared_html = (
        "<html><head><title>Shared application</title></head><body>"
        f"<div id='root'><h1>Shared application</h1><p>{shared_words}</p></div>"
        "<script src='/application.js'></script></body></html>"
    )
    rendered = {
        url: render_result(url, meaningful_html(f"Rendered route {index}", 80))
        for index, url in enumerate(urls)
    }
    renderer = FakeRenderer(rendered)

    pages = extract_audit_pages(
        [response(url, shared_html) for url in urls],
        browser_enabled=True,
        browser_timeout_ms=4_000,
        browser_concurrency=2,
        browser_fallback_limit=10,
        shared_shell_browser_limit=30,
        renderer=renderer,
    )

    browser_pages = [page for page in pages if page.extraction_method == "browser"]
    assert sum(len(call[0]) for call in renderer.calls) == 30
    assert len(browser_pages) == 30
    assert len({page.content_sha256 for page in browser_pages}) == 30
    assert all(
        page.evidence["identity"]["browser_fallback_reason"] == "shared_http_shell"
        for page in browser_pages
    )
    assert sum(page.extraction_method == "failed" for page in pages) == 110

    selected = select_geo_important_pages(
        pages,
        audited_url=urls[0],
        homepage_url="https://example.test/",
        homepage_links=set(),
        sitemap_urls=set(urls),
        limit=30,
    )
    assert len(selected) == 30
    assert not any(page.is_duplicate for page in selected)


def test_browser_probe_keeps_genuinely_identical_aliases_as_duplicates():
    urls = [
        "https://example.test/guide/alias",
        "https://example.test/comparison/alias",
        "https://example.test/resources/alias",
    ]
    shared_words = " ".join(f"shared-{index}" for index in range(328))
    shared_html = f"<html><body><h1>Shared</h1><p>{shared_words}</p></body></html>"
    rendered_html = meaningful_html("Same rendered destination", 80)
    renderer = FakeRenderer({
        url: render_result(url, rendered_html) for url in urls
    })

    pages = extract_audit_pages(
        [response(url, shared_html) for url in urls],
        browser_enabled=True,
        browser_timeout_ms=4_000,
        browser_concurrency=2,
        browser_fallback_limit=10,
        shared_shell_browser_limit=30,
        renderer=renderer,
    )

    assert len(renderer.calls) == 1
    assert all(page.extraction_method == "http" for page in pages)
    assert sum(page.is_duplicate for page in pages) == 2


def test_bounded_runner_respects_concurrency():
    active = 0
    peak = 0

    async def worker(url):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return render_result(url, meaningful_html(url))

    results = asyncio.run(run_bounded([str(index) for index in range(8)], worker, 2))

    assert len(results) == 8
    assert peak == 2
