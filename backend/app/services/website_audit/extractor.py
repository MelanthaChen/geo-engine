import hashlib
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.website_audit.crawler import CrawlResponse


@dataclass
class PageExtract:
    url: str
    page_title: str | None
    meta_description: str | None
    h1: str | None
    status_code: int | None
    word_count: int
    internal_link_count: int
    external_link_count: int
    body_text: str
    content_sha256: str | None = None
    is_duplicate: bool = False
    duplicate_of_url: str | None = None
    question_heading_count: int = 0
    detected_qa_pair_count: int = 0
    faq_like_heading_count: int = 0
    faq_page_schema_detected: bool = False


def extract_pages(responses: list[CrawlResponse]) -> list[PageExtract]:
    pages = [extract_page(response) for response in responses]
    first_url_by_hash: dict[str, str] = {}
    for page in pages:
        if page.status_code is None or not 200 <= page.status_code < 300 or not page.body_text:
            continue
        digest = normalized_content_sha256(page.body_text)
        page.content_sha256 = digest
        if digest in first_url_by_hash:
            page.is_duplicate = True
            page.duplicate_of_url = first_url_by_hash[digest]
        else:
            first_url_by_hash[digest] = page.url
    return pages


def extract_page(response: CrawlResponse) -> PageExtract:
    if not response.html:
        return PageExtract(
            url=response.url,
            page_title=None,
            meta_description=None,
            h1=None,
            status_code=response.status_code,
            word_count=0,
            internal_link_count=0,
            external_link_count=0,
            body_text="",
        )

    soup = BeautifulSoup(response.html, "html.parser")

    faq_page_schema_detected = detect_faq_page_schema(soup)
    question_heading_count, detected_qa_pair_count, faq_like_heading_count = (
        extract_faq_structure(soup)
    )

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = clean_text(soup.title.string) if soup.title and soup.title.string else None
    meta_description = extract_meta_description(soup)
    h1 = extract_h1(soup)
    body_text = clean_text(soup.get_text(" "))
    words = re.findall(r"\b[\w'-]+\b", body_text)
    internal_links, external_links = count_links(soup, response.url)

    return PageExtract(
        url=response.url,
        page_title=title,
        meta_description=meta_description,
        h1=h1,
        status_code=response.status_code,
        word_count=len(words),
        internal_link_count=internal_links,
        external_link_count=external_links,
        body_text=body_text,
        question_heading_count=question_heading_count,
        detected_qa_pair_count=detected_qa_pair_count,
        faq_like_heading_count=faq_like_heading_count,
        faq_page_schema_detected=faq_page_schema_detected,
    )


def detect_faq_page_schema(soup: BeautifulSoup) -> bool:
    return any(
        '"FAQPage"' in (script.string or script.get_text(" "))
        for script in soup.find_all("script", attrs={"type": "application/ld+json"})
    )


def extract_faq_structure(soup: BeautifulSoup) -> tuple[int, int, int]:
    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    question_headings = []
    faq_like_headings = 0
    for heading in headings:
        text = clean_text(heading.get_text(" "))
        normalized = text.lower().rstrip(":")
        if text.endswith("?"):
            question_headings.append(heading)
        if normalized in {"faq", "faqs", "frequently asked questions", "questions and answers", "q&a"}:
            faq_like_headings += 1

    qa_pairs = 0
    for heading in question_headings:
        sibling = heading.find_next_sibling(True)
        while sibling is not None and sibling.name in {"script", "style", "noscript", "svg"}:
            sibling = sibling.find_next_sibling(True)
        if sibling is not None and not re.match(r"^h[1-6]$", sibling.name or ""):
            if clean_text(sibling.get_text(" ")):
                qa_pairs += 1
    return len(question_headings), qa_pairs, faq_like_headings


def extract_meta_description(soup: BeautifulSoup) -> str | None:
    tag = soup.find("meta", attrs={"name": "description"})

    if not tag:
        tag = soup.find("meta", attrs={"property": "og:description"})

    content = tag.get("content") if tag else None

    return clean_text(content) if content else None


def extract_h1(soup: BeautifulSoup) -> str | None:
    tag = soup.find("h1")

    return clean_text(tag.get_text(" ")) if tag else None


def count_links(soup: BeautifulSoup, page_url: str) -> tuple[int, int]:
    current_host = urlparse(page_url).netloc
    internal_count = 0
    external_count = 0

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()

        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        host = urlparse(urljoin(page_url, href)).netloc

        if host == current_host:
            internal_count += 1
        else:
            external_count += 1

    return internal_count, external_count


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def normalized_content_sha256(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", clean_text(value))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
