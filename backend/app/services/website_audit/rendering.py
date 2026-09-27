from collections import Counter

from bs4 import BeautifulSoup

from app.services.website_audit.browser_renderer import BrowserRenderer
from app.services.website_audit.crawler import CrawlResponse
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

    if not browser_enabled or not candidates:
        if not browser_enabled:
            for _, page, reasons in candidates:
                mark_failed(
                    page,
                    "HTTP extraction insufficient "
                    f"({'; '.join(reasons)}); browser fallback is disabled.",
                )
        apply_duplicate_detection(http_pages)
        return http_pages

    attempted = candidates[:browser_fallback_limit]
    for _, page, reasons in candidates[browser_fallback_limit:]:
        mark_failed(
            page,
            "HTTP extraction insufficient "
            f"({'; '.join(reasons)}); browser fallback limit reached.",
        )

    renderer = renderer or BrowserRenderer()
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

        browser_page = extract_page(
            CrawlResponse(
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
            )
        )
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
        browser_page.extraction_method = "browser"
        browser_page.evidence["identity"]["extraction_method"] = "browser"
        browser_page.extraction_failure_reason = None
        browser_page.http_word_count = http_page.word_count
        browser_page.browser_word_count = browser_page.word_count
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
        any("distinct URLs" in reason for reason in fallback_reasons)
        and normalized_content_sha256(browser_page.body_text)
        != normalized_content_sha256(http_page.body_text)
    )
    enough_evidence = browser_page.word_count >= 40 or (
        browser_page.word_count >= 15 and bool(browser_page.h1 or browser_page.page_title)
    )
    return changed and enough_evidence and (
        word_gain or gained_structure or route_specific_change
    )


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
