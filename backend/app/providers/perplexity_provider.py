from __future__ import annotations

from dataclasses import dataclass
import threading
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.services.session_resolver import SessionResolver


PERPLEXITY_HOME_URL = "https://www.perplexity.ai/"

_perplexity_lock = threading.Lock()


@dataclass
class PerplexityWebResult:
    response: str
    citations: list[str]
    latency_ms: int

    def to_text(self) -> str:
        parts = [self.response.strip()]

        if self.citations:
            parts.append(
                "Citations:\n"
                + "\n".join(
                    f"{index}. {url}"
                    for index, url in enumerate(self.citations, start=1)
                )
            )

        parts.append(f"Response time: {self.latency_ms} ms")

        return "\n\n".join(part for part in parts if part)


class PerplexityProvider:
    name = "perplexity"

    def __init__(self):
        self.session_resolver = SessionResolver()

    def generate_text(
        self,
        *,
        system_prompt: str | None,
        user_prompt: str,
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
    ) -> str:
        prompt = self._build_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return self._run_perplexity_query(prompt).to_text()

    def generate_messages(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
    ) -> str:
        prompt = "\n\n".join(
            f"{message.get('role', 'user').title()}:\n{message.get('content', '')}"
            for message in messages
            if message.get("content")
        )

        return self._run_perplexity_query(prompt).to_text()

    def run_query(self, **kwargs):
        return self.generate_text(**kwargs)

    def generate_content(self, **kwargs):
        return self.generate_text(**kwargs)

    def run_citation_test(self, **kwargs):
        return self.generate_text(**kwargs)

    def run_experiment(self, **kwargs):
        return self.generate_text(**kwargs)

    def _run_perplexity_query(self, prompt: str) -> PerplexityWebResult:
        profile_dir = self.session_resolver.resolve_profile("perplexity")
        started_at = time.perf_counter()

        with _perplexity_lock:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    channel="chrome",
                    headless=False,
                    locale="en-US",
                    timezone_id="America/New_York",
                )

                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    page.goto(PERPLEXITY_HOME_URL, wait_until="domcontentloaded")
                    self._submit_query(page, prompt)
                    response = self._wait_for_response(page, prompt)
                    citations = self._extract_citations(page)
                    latency_ms = int((time.perf_counter() - started_at) * 1000)

                    return PerplexityWebResult(
                        response=response,
                        citations=citations,
                        latency_ms=latency_ms,
                    )
                finally:
                    context.close()

    def _submit_query(self, page, prompt: str) -> None:
        composer_selectors = [
            "textarea[placeholder*='Ask']",
            "textarea[placeholder*='anything']",
            "textarea",
            "[contenteditable='true'][role='textbox']",
            "div[contenteditable='true']",
            "[role='textbox']",
        ]

        composer = None

        for selector in composer_selectors:
            locator = page.locator(selector).first

            try:
                locator.wait_for(state="visible", timeout=8000)
                composer = locator
                break
            except PlaywrightTimeoutError:
                continue

        if composer is None:
            raise RuntimeError(
                "Perplexity query box was not found. "
                "Run `python save_platform_state.py perplexity` and verify "
                "the saved profile can access perplexity.ai."
            )

        tag_name = composer.evaluate("(el) => el.tagName.toLowerCase()")

        composer.click()

        if tag_name in {"textarea", "input"}:
            composer.fill(prompt)
        else:
            handle = composer.element_handle()
            handle.evaluate(
                """(element, value) => {
                    element.focus();
                    element.textContent = value;
                    element.dispatchEvent(
                        new InputEvent('input', {
                            bubbles: true,
                            inputType: 'insertText',
                            data: value
                        })
                    );
                }""",
                prompt,
            )

        page.keyboard.press("Enter")

    def _wait_for_response(self, page, prompt: str) -> str:
        last_text = ""
        stable_count = 0
        deadline = time.time() + 120

        while time.time() < deadline:
            page.wait_for_timeout(1500)
            current_text = self._extract_response_text(page, prompt)

            if not current_text or len(current_text) < 80:
                continue

            if current_text == last_text:
                stable_count += 1
            else:
                stable_count = 0
                last_text = current_text

            if stable_count >= 2:
                return current_text

        if last_text:
            return last_text

        raise RuntimeError("Perplexity did not produce a readable response.")

    def _extract_response_text(self, page, prompt: str) -> str:
        prompt_preview = prompt.strip()[:120]

        candidates = page.evaluate(
            """(promptPreview) => {
                const selectors = [
                    'main article',
                    'article',
                    '[data-testid*="answer"]',
                    '[class*="answer"]',
                    '[class*="prose"]',
                    'main'
                ];
                const seen = new Set();
                const results = [];

                for (const selector of selectors) {
                    for (const element of document.querySelectorAll(selector)) {
                        if (seen.has(element)) continue;
                        seen.add(element);

                        const rect = element.getBoundingClientRect();
                        const style = window.getComputedStyle(element);
                        const text = (element.innerText || '').trim();

                        if (
                            rect.width > 0 &&
                            rect.height > 0 &&
                            style.visibility !== 'hidden' &&
                            style.display !== 'none' &&
                            text.length > 0
                        ) {
                            results.push(text);
                        }
                    }
                }

                return results
                    .filter((text) => !promptPreview || !text.startsWith(promptPreview))
                    .sort((a, b) => b.length - a.length);
            }""",
            prompt_preview,
        )

        if not candidates:
            return ""

        return self._clean_response_text(candidates[0], prompt)

    def _extract_citations(self, page) -> list[str]:
        urls = page.evaluate(
            """() => {
                const anchors = Array.from(document.querySelectorAll('main a[href]'));

                return anchors
                    .map((anchor) => anchor.href)
                    .filter((href) =>
                        href &&
                        href.startsWith('http') &&
                        !href.includes('perplexity.ai') &&
                        !href.includes('javascript:')
                    );
            }"""
        )
        deduped = []

        for url in urls:
            if url not in deduped:
                deduped.append(url)

        return deduped[:10]

    @staticmethod
    def _build_prompt(
        *,
        system_prompt: str | None,
        user_prompt: str,
    ) -> str:
        if not system_prompt:
            return user_prompt

        return f"{system_prompt.strip()}\n\n{user_prompt.strip()}"

    @staticmethod
    def _clean_response_text(text: str, prompt: str) -> str:
        cleaned = text.strip()
        prompt_text = prompt.strip()

        if prompt_text and cleaned.startswith(prompt_text):
            cleaned = cleaned[len(prompt_text):].strip()

        return cleaned
