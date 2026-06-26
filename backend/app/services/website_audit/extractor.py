import re
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


def extract_pages(responses: list[CrawlResponse]) -> list[PageExtract]:
    return [extract_page(response) for response in responses]


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
    )


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
