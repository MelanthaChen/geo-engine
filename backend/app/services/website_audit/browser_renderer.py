import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserRenderResult:
    requested_url: str
    final_url: str
    status_code: int | None
    html: str
    error: str | None = None


async def run_bounded(
    urls: list[str],
    worker: Callable[[str], Awaitable[BrowserRenderResult]],
    concurrency: int,
) -> list[BrowserRenderResult]:
    """Run render work with an observable, testable concurrency bound."""
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(url: str) -> BrowserRenderResult:
        async with semaphore:
            return await worker(url)

    return list(await asyncio.gather(*(guarded(url) for url in urls)))


class BrowserRenderer:
    """Lazy, shared-browser Chromium renderer used only by Website Audit."""

    def render_many(
        self,
        urls: list[str],
        *,
        timeout_ms: int,
        concurrency: int,
    ) -> dict[str, BrowserRenderResult]:
        if not urls:
            return {}
        return asyncio.run(self._render_many(urls, timeout_ms, concurrency))

    async def _render_many(
        self,
        urls: list[str],
        timeout_ms: int,
        concurrency: int,
    ) -> dict[str, BrowserRenderResult]:
        try:
            from playwright.async_api import (
                TimeoutError as PlaywrightTimeoutError,
                async_playwright,
            )

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (compatible; GEOPlatformAudit/1.0; "
                        "+https://geo-engine.example/audit)"
                    )
                )

                async def render(url: str) -> BrowserRenderResult:
                    page = await context.new_page()
                    try:
                        response = await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                        # Do not wait for network-idle. A short DOM-stability wait lets
                        # common hydration/lazy-content tasks settle while remaining bounded.
                        await self._wait_for_dom_content(page, timeout_ms)
                        return BrowserRenderResult(
                            requested_url=url,
                            final_url=page.url,
                            status_code=response.status if response else None,
                            html=await page.content(),
                        )
                    except PlaywrightTimeoutError:
                        return BrowserRenderResult(
                            requested_url=url,
                            final_url=page.url or url,
                            status_code=None,
                            html="",
                            error="Browser rendering timed out.",
                        )
                    except Exception as exc:  # pragma: no cover - browser/OS specific
                        return BrowserRenderResult(
                            requested_url=url,
                            final_url=page.url or url,
                            status_code=None,
                            html="",
                            error=f"Browser rendering failed: {type(exc).__name__}.",
                        )
                    finally:
                        await page.close()

                results = await run_bounded(urls, render, concurrency)
                await context.close()
                await browser.close()
                return {result.requested_url: result for result in results}
        except Exception as exc:  # Browser missing or unable to launch.
            if "executable doesn't exist" in str(exc).lower():
                reason = "Browser rendering unavailable: Chromium executable is not installed."
            else:
                reason = f"Browser rendering unavailable: {type(exc).__name__}."
            return {
                url: BrowserRenderResult(url, url, None, "", reason)
                for url in urls
            }

    @staticmethod
    async def _wait_for_dom_content(page, timeout_ms: int) -> None:
        budget_ms = min(max(timeout_ms // 3, 250), 2_000)
        interval_ms = 200
        previous_length = -1
        stable_ticks = 0
        elapsed = 0
        while elapsed < budget_ms:
            length = await page.evaluate(
                "() => (document.body && document.body.innerText || '').trim().length"
            )
            if length >= 200 and length == previous_length:
                stable_ticks += 1
                if stable_ticks >= 2:
                    return
            else:
                stable_ticks = 0
            previous_length = length
            await page.wait_for_timeout(interval_ms)
            elapsed += interval_ms
