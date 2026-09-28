from collections import Counter

from bs4 import BeautifulSoup

from app.services.website_audit.browser_renderer import BrowserRenderer
from app.services.website_audit.crawler import (
    CrawlResponse,
    path_family,
    path_segments,
    round_robin_families,
)
from app.services.website_audit.extractor import (
    PageExtract,
    apply_duplicate_detection,
    extract_page,
    normalized_content_sha256,
)


def extract_audit_pages(
    responses: list[CrawlResponse],
    *,
    browser_enabled: bool,
    browser_timeout_ms: int,
    browser_concurrency: int,
    browser_fallback_limit: int,
    shared_shell_browser_limit: int = 30,
    renderer=None,
) -> list[PageExtract]:
    """HTTP-first extraction with bounded, selected-page-only browser fallback."""
    http_pages = [extract_page(response) for response in responses]
    provisional_hashes = Counter(
        normalized_content_sha256(page.body_text)
        for page in http_pages
        if page.body_text
    )
    candidates: list[tuple[CrawlResponse, PageExtract, tuple[str, ...]]] = []
    for response, page in zip(responses, http_pages, strict=True):
        reasons = needs_browser_render(
            response,
            page,
            duplicate_hash_count=(
                provisional_hashes[normalized_content_sha256(page.body_text)]
                if page.body_text
                else 0
            ),
        )
        if reasons:
            candidates.append((response, page, reasons))

    normal_candidate_urls = {response.url for response, _, _ in candidates}
    suspicious_clusters = shared_http_shell_clusters(
        responses,
        http_pages,
        excluded_urls=normal_candidate_urls,
    )

    if not browser_enabled:
        if not browser_enabled:
            for _, page, reasons in candidates:
                mark_failed(
                    page,
                    "HTTP extraction insufficient "
                    f"({'; '.join(reasons)}); browser fallback is disabled.",
                )
        apply_duplicate_detection(http_pages)
        return http_pages

    # A normal server-rendered crawl must not touch the browser runtime at all.
    # This keeps HTTP-only audits independent from Playwright installation and
    # browser startup failures.
    if not candidates and not suspicious_clusters:
        apply_duplicate_detection(http_pages)
        return http_pages

    renderer = renderer or BrowserRenderer()
    confirmed_shell_urls: list[str] = []
    confirmed_cluster_urls: set[str] = set()
    cached_rendered = {}
    remaining_probe_budget = browser_fallback_limit
    for cluster in suspicious_clusters:
        if remaining_probe_budget < 2:
            break
        probe_urls = structurally_diverse_urls(
            [response.url for response, _ in cluster],
            limit=min(3, remaining_probe_budget),
        )
        if len(probe_urls) < 2:
            continue
        probe_results = renderer.render_many(
            probe_urls,
            timeout_ms=browser_timeout_ms,
            concurrency=browser_concurrency,
        )
        cached_rendered.update(probe_results)
        remaining_probe_budget -= len(probe_urls)
        browser_hashes = {
            normalized_content_sha256(page.body_text)
            for url in probe_urls
            if (page := extracted_browser_page(
                next(response for response, _ in cluster if response.url == url),
                probe_results.get(url),
            )) is not None
            and page.word_count >= 15
        }
        if len(browser_hashes) > 1:
            confirmed_cluster_urls.update(response.url for response, _ in cluster)
            confirmed_shell_urls.extend(
                url for url in structurally_diverse_urls(
                    [response.url for response, _ in cluster],
                    limit=shared_shell_browser_limit,
                )
                if url not in confirmed_shell_urls
            )

    confirmed_shell_urls = confirmed_shell_urls[:shared_shell_browser_limit]
    confirmed_shell_set = set(confirmed_shell_urls)
    if confirmed_shell_urls:
        remaining_urls = [
            url for url in confirmed_shell_urls if url not in cached_rendered
        ]
        if remaining_urls:
            cached_rendered.update(renderer.render_many(
                remaining_urls,
                timeout_ms=browser_timeout_ms,
                concurrency=browser_concurrency,
            ))
        response_by_url = {response.url: response for response in responses}
        by_url = {page.url: index for index, page in enumerate(http_pages)}
        for url in confirmed_shell_urls:
            response = response_by_url[url]
            http_page = http_pages[by_url[url]]
            browser_page = extracted_browser_page(response, cached_rendered.get(url))
            if browser_page is None:
                mark_failed(http_page, "Browser verification of shared HTTP shell failed.")
                continue
            if not rendered_content_is_materially_richer(
                http_page,
                browser_page,
                fallback_reasons=("shared_http_shell",),
            ):
                mark_failed(
                    http_page,
                    "Rendered content did not provide distinct usable evidence after shared-shell verification.",
                )
                continue
            admit_browser_page(
                browser_page,
                http_page,
                reason="shared_http_shell",
            )
            http_pages[by_url[url]] = browser_page

        for url in confirmed_cluster_urls - confirmed_shell_set:
            page = http_pages[by_url[url]]
            mark_failed(
                page,
                "Confirmed shared HTTP shell; route was outside the bounded browser-render sample.",
            )

    if not candidates:
        apply_duplicate_detection(http_pages)
        return http_pages

    attempted = candidates[:browser_fallback_limit]
    for _, page, reasons in candidates[browser_fallback_limit:]:
        mark_failed(
            page,
            "HTTP extraction insufficient "
            f"({'; '.join(reasons)}); browser fallback limit reached.",
        )

    rendered = renderer.render_many(
        [response.url for response, _, _ in attempted],
        timeout_ms=browser_timeout_ms,
        concurrency=browser_concurrency,
    )
    by_url = {page.url: index for index, page in enumerate(http_pages)}
    for response, http_page, reasons in attempted:
        result = rendered.get(response.url)
        if result is None or result.error or not result.html:
            mark_failed(
                http_page,
                (result.error if result else "Browser rendering returned no result.")
                or "Browser rendering returned no HTML.",
            )
            continue

        browser_page = extracted_browser_page(response, result)
        if browser_page is None:
            mark_failed(http_page, "Browser rendering returned no usable HTML.")
            continue
        if not rendered_content_is_materially_richer(
            http_page,
            browser_page,
            fallback_reasons=reasons,
        ):
            mark_failed(
                http_page,
                "Rendered content remained insufficient or was not materially richer than HTTP evidence.",
            )
            continue
        admit_browser_page(browser_page, http_page, reason="http_extraction_insufficient")
        http_pages[by_url[response.url]] = browser_page

    apply_duplicate_detection(http_pages)
    return http_pages


def needs_browser_render(
    response: CrawlResponse,
    page: PageExtract,
    *,
    duplicate_hash_count: int = 1,
) -> tuple[str, ...]:
    """Return deterministic insufficiency reasons; an empty tuple means HTTP wins."""
    if (
        response.status_code is None
        or not 200 <= response.status_code < 300
        or not response.html_accepted
        or not response.html
    ):
        return ()

    soup = BeautifulSoup(response.html, "html.parser")
    shell_marker = bool(soup.select_one(
        "#root, #app, #__next, #__nuxt, [data-reactroot], [data-react-app]"
    ))
    script_count = len(soup.find_all("script"))
    script_text_size = sum(len(str(script)) for script in soup.find_all("script"))
    visible_size = len(page.body_text)
    script_heavy = (
        script_count >= 3
        and script_text_size > max(visible_size * 2, 500)
    )
    navigation_words = sum(
        len(element.get_text(" ", strip=True).split())
        for element in soup.select("nav, header, footer")
    )
    navigation_dominated = (
        0 < page.word_count < 80
        and navigation_words / page.word_count >= 0.75
    )
    missing_core = not page.h1 and not page.page_title and page.word_count < 30
    identical_shell = duplicate_hash_count > 1 and page.word_count < 100
    low_content = page.word_count < 40
    extremely_low = page.word_count < 10

    reasons: list[str] = []
    if page.word_count == 0 and (shell_marker or script_heavy):
        reasons.append("empty extracted body")
    if low_content and shell_marker and (
        extremely_low or not page.h1 or script_heavy or identical_shell
    ):
        reasons.append("app-shell marker with little extracted content")
    if low_content and script_heavy:
        reasons.append("script-heavy markup with little extracted content")
    if missing_core and (shell_marker or script_heavy):
        reasons.append("no meaningful title, H1, or body evidence")
    if identical_shell and (shell_marker or script_heavy):
        reasons.append("distinct URLs share the same low-content HTTP shell")
    if navigation_dominated and (shell_marker or script_heavy):
        reasons.append("extracted body is dominated by navigation or app-shell text")
    if extremely_low and (shell_marker or script_heavy):
        reasons.append("extremely low extracted word count corroborated by application markup")
    return tuple(dict.fromkeys(reasons))


def rendered_content_is_materially_richer(
    http_page: PageExtract,
    browser_page: PageExtract,
    *,
    fallback_reasons: tuple[str, ...] = (),
) -> bool:
    if browser_page.status_code is None or not 200 <= browser_page.status_code < 300:
        return False
    if browser_page.word_count < 15 or not browser_page.body_text:
        return False
    changed = browser_page.body_text != http_page.body_text
    gained_structure = bool(browser_page.h1 and not http_page.h1)
    word_gain = browser_page.word_count >= http_page.word_count + max(
        8, http_page.word_count // 4
    )
    route_specific_change = (
        any(
            "distinct URLs" in reason or reason == "shared_http_shell"
            for reason in fallback_reasons
        )
        and normalized_content_sha256(browser_page.body_text)
        != normalized_content_sha256(http_page.body_text)
    )
    enough_evidence = browser_page.word_count >= 40 or (
        browser_page.word_count >= 15 and bool(browser_page.h1 or browser_page.page_title)
    )
    return changed and enough_evidence and (
        word_gain or gained_structure or route_specific_change
    )


def shared_http_shell_clusters(
    responses: list[CrawlResponse],
    pages: list[PageExtract],
    *,
    excluded_urls: set[str],
    minimum_cluster_size: int = 3,
) -> list[list[tuple[CrawlResponse, PageExtract]]]:
    """Find structurally diverse routes sharing one non-empty HTTP representation."""
    grouped: dict[str, list[tuple[CrawlResponse, PageExtract]]] = {}
    for response, page in zip(responses, pages, strict=True):
        if response.url in excluded_urls or not page.body_text:
            continue
        digest = normalized_content_sha256(page.body_text)
        grouped.setdefault(digest, []).append((response, page))
    clusters = []
    for members in grouped.values():
        structures = {
            (path_family(response.url), len(path_segments(response.url)))
            for response, _ in members
        }
        if len(members) >= minimum_cluster_size and len(structures) >= 2:
            clusters.append(members)
    return sorted(clusters, key=lambda members: (-len(members), members[0][0].url))


def structurally_diverse_urls(urls: list[str], *, limit: int) -> list[str]:
    if not urls or limit < 1:
        return []
    first = urls[0]
    selected = [first]
    selected.extend(round_robin_families(
        set(urls) - {first},
        limit=limit - 1,
    ))
    return selected[:limit]


def extracted_browser_page(response: CrawlResponse, result) -> PageExtract | None:
    if result is None or result.error or not result.html:
        return None
    return extract_page(CrawlResponse(
        url=result.final_url or response.url,
        status_code=(
            result.status_code
            if result.status_code is not None
            else response.status_code
        ),
        html=result.html,
        content_type="text/html",
        html_accepted=True,
        requested_url=response.requested_url or response.url,
    ))


def admit_browser_page(
    browser_page: PageExtract,
    http_page: PageExtract,
    *,
    reason: str,
) -> None:
    browser_page.extraction_method = "browser"
    identity = browser_page.evidence.setdefault("identity", {})
    identity["extraction_method"] = "browser"
    identity["browser_fallback_reason"] = reason
    browser_page.evidence["browser_fallback_reason"] = reason
    browser_page.extraction_failure_reason = None
    browser_page.http_word_count = http_page.word_count
    browser_page.browser_word_count = browser_page.word_count


def mark_failed(page: PageExtract, reason: str) -> None:
    page.extraction_method = "failed"
    page.extraction_failure_reason = reason
    page.http_word_count = page.word_count
    page.browser_word_count = None
    page.body_text = ""
    page.word_count = 0
    page.internal_link_count = 0
    page.external_link_count = 0
    page.content_sha256 = None
    page.is_duplicate = False
    page.duplicate_of_url = None
    if page.evidence:
        page.evidence.setdefault("identity", {})["extraction_method"] = "failed"
        page.evidence["extraction_failure_reason"] = reason
