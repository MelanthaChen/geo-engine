import json
import re
from collections import Counter
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


EVIDENCE_VERSION = "website-audit-evidence-v1"
STOP_WORDS = {
    "a", "about", "after", "all", "also", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "between",
    "both", "but", "by", "can", "could", "do", "does", "each", "for",
    "from", "had", "has", "have", "he", "her", "here", "how", "i", "if",
    "in", "into", "is", "it", "its", "more", "most", "not", "of", "on",
    "or", "our", "out", "over", "she", "should", "so", "some", "such",
    "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "to", "under", "up", "use", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "will",
    "with", "would", "you", "your",
}
REFERENCE_TERMS = re.compile(
    r"\b(?:according to|source|sources|study|studies|research|report|paper|"
    r"journal|reference|references|evidence|data from|published by)\b",
    re.IGNORECASE,
)
EXPLANATORY_TERMS = re.compile(
    r"\b(?:how|what|why|guide|step|learn|help|explain|understand|works|"
    r"allows|provides|method|process)\b",
    re.IGNORECASE,
)
METHODOLOGY_TERMS = re.compile(
    r"\b(?:methodology|method|research|analysis|evidence|dataset|experiment|"
    r"measured|survey|study|findings)\b",
    re.IGNORECASE,
)
CREDENTIAL_TERMS = re.compile(
    r"\b(?:phd|m\.d\.|professor|researcher|certified|licensed|specialist|"
    r"expert|years of experience)\b",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(
    r"(?<![\w])(?:[$€£¥]\s*)?\d[\d,.]*(?:\s?%|\s+(?:percent|million|"
    r"billion|thousand|years?|months?|days?|users?|people|km|kg|ms|seconds?))?",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
CURRENCY_PATTERN = re.compile(r"(?:[$€£¥]\s*\d[\d,.]*|\b\d[\d,.]*\s?(?:USD|EUR|GBP|CNY)\b)", re.IGNORECASE)
PERCENT_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:%|percent\b)",
    re.IGNORECASE,
)


def build_page_evidence(
    *,
    html: str,
    final_url: str,
    requested_url: str,
    body_text: str,
    extraction_method: str,
) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    headings = {
        level: [clean_text(tag.get_text(" ")) for tag in soup.find_all(level) if clean_text(tag.get_text(" "))]
        for level in ("h1", "h2", "h3")
    }
    title = clean_text(soup.title.string) if soup.title and soup.title.string else None
    meta_description = meta_content(soup, "description") or meta_property(soup, "og:description")
    canonical = canonical_url(soup, final_url)
    robots = robots_directives(soup)
    schema_payloads = json_ld_payloads(soup)
    schema_types = sorted(schema_type_set(schema_payloads))
    link_evidence = extract_link_evidence(soup, final_url)
    authorship = extract_authorship(soup, schema_payloads)
    faq = extract_faq_evidence(soup, body_text)
    statistics = extract_statistics(body_text)
    quotations = extract_quotations(soup, body_text)
    terms = extract_term_evidence(
        body_text=body_text,
        emphasized_text=" ".join(filter(None, [title, *headings["h1"], *headings["h2"], *headings["h3"]])),
    )
    readability = extract_structural_readability(soup, body_text, headings)
    authority = extract_authority_evidence(
        body_text,
        authorship,
        link_evidence,
        schema_types,
    )

    return {
        "version": EVIDENCE_VERSION,
        "identity": {
            "requested_url": requested_url,
            "final_url": final_url,
            "canonical_url": canonical,
            "path_family": path_family(final_url),
            "extraction_method": extraction_method,
        },
        "metadata": {
            "title": title,
            "meta_description": meta_description,
            "canonical_url": canonical,
            "robots_directives": robots,
        },
        "headings": {
            "h1": headings["h1"],
            "h2": headings["h2"],
            "h3": headings["h3"],
            "counts": {level: len(values) for level, values in headings.items()},
        },
        "content": {
            "body_text": body_text,
            "preview": body_text[:500],
            "word_count": len(tokenize(body_text)),
            "paragraph_count": len([
                tag for tag in soup.find_all("p") if clean_text(tag.get_text(" "))
            ]),
            "list_count": len(soup.find_all(["ul", "ol"])),
        },
        "links": link_evidence,
        "structured_data": {
            "schema_types": schema_types,
            "faq_page_present": "FAQPage" in schema_types,
            "article_present": any(value in schema_types for value in ("Article", "NewsArticle", "BlogPosting")),
            "organization_present": "Organization" in schema_types,
            "person_or_author_present": "Person" in schema_types or bool(authorship["author_name"]),
        },
        "authorship": authorship,
        "strategies": {
            "faq": faq,
            "statistics": statistics,
            "citation": {
                "external_link_count": len(link_evidence["external_urls"]),
                "reference_like_link_count": len(link_evidence["reference_like_links"]),
                "distinct_reference_domains": link_evidence["reference_domains"],
                "attribution_phrase_count": len(reference_phrase_snippets(body_text)),
                "attribution_snippets": reference_phrase_snippets(body_text),
            },
            "quotation": quotations,
            "authoritative": authority,
            "technical_terms": {
                "prominent_terms": terms["prominent_terms"],
                "repeated_terms": terms["top_terms"],
                "glossary_definition_count": glossary_definition_count(soup, body_text),
            },
            "easy_to_understand": readability,
            "fluency": {
                **readability,
                "note": "Structural evidence only; no objective fluency score is inferred.",
            },
            "unique_words": {
                "unique_token_count": terms["unique_token_count"],
                "lexical_diversity_ratio": terms["lexical_diversity_ratio"],
                "meaningful_token_count": terms["meaningful_token_count"],
            },
            "keyword_stuffing": {
                "highest_frequency_terms": terms["top_terms"],
                "top_term_concentration": terms["top_term_concentration"],
                "repeated_phrases": terms["repeated_phrases"],
                "note": "Frequency evidence only; no keyword-stuffing label is assigned.",
            },
        },
    }


def extract_link_evidence(soup: BeautifulSoup, page_url: str) -> dict:
    current_host = (urlparse(page_url).hostname or "").lower()
    internal: list[str] = []
    external: list[str] = []
    references: list[dict] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(page_url, href)
        host = (urlparse(url).hostname or "").lower()
        target = internal if host == current_host else external
        if url not in target:
            target.append(url)
        if host and host != current_host:
            anchor_text = clean_text(anchor.get_text(" "))
            context = clean_text(anchor.parent.get_text(" "))[:300] if anchor.parent else anchor_text
            path = urlparse(url).path.lower()
            if (
                REFERENCE_TERMS.search(f"{anchor_text} {context}")
                or re.fullmatch(r"\[?\d+\]?", anchor_text)
                or any(term in path for term in ("/research", "/study", "/report", "/paper", "/publication", "/doi"))
            ):
                references.append({
                    "url": url,
                    "domain": host,
                    "anchor_text": anchor_text,
                    "context": context,
                })
    return {
        "internal_urls": internal[:200],
        "external_urls": external[:200],
        "external_domains": sorted({(urlparse(url).hostname or "").lower() for url in external if urlparse(url).hostname}),
        "reference_like_links": references[:100],
        "reference_domains": sorted({item["domain"] for item in references}),
    }


def extract_faq_evidence(soup: BeautifulSoup, body_text: str) -> dict:
    question_headings = []
    faq_headings = []
    qa_pairs = 0
    for heading in soup.find_all(re.compile(r"^h[1-6]$")):
        text = clean_text(heading.get_text(" "))
        normalized = text.lower().rstrip(":")
        if text.endswith("?"):
            question_headings.append(text)
            sibling = heading.find_next_sibling(True)
            while sibling is not None and sibling.name in {"script", "style", "noscript", "svg"}:
                sibling = sibling.find_next_sibling(True)
            if sibling is not None and not re.match(r"^h[1-6]$", sibling.name or "") and clean_text(sibling.get_text(" ")):
                qa_pairs += 1
        if normalized in {"faq", "faqs", "frequently asked questions", "questions and answers", "q&a"}:
            faq_headings.append(text)
    schema_types = schema_type_set(json_ld_payloads(soup))
    return {
        "question_heading_count": len(question_headings),
        "question_headings": question_headings[:30],
        "detected_qa_pair_count": qa_pairs,
        "faq_like_heading_count": len(faq_headings),
        "faq_like_headings": faq_headings[:20],
        "faq_page_schema_present": "FAQPage" in schema_types,
        "explanatory_text_present": bool(EXPLANATORY_TERMS.search(body_text)),
    }


def extract_statistics(text: str) -> dict:
    matches = list(NUMBER_PATTERN.finditer(text))
    return {
        "numeric_claim_count": len(matches),
        "percentage_count": len(PERCENT_PATTERN.findall(text)),
        "currency_value_count": len(CURRENCY_PATTERN.findall(text)),
        "date_or_year_count": len(YEAR_PATTERN.findall(text)),
        "quantitative_snippets": snippets_for_matches(text, matches)[:12],
    }


def extract_quotations(soup: BeautifulSoup, text: str) -> dict:
    blockquotes = [clean_text(tag.get_text(" ")) for tag in soup.find_all("blockquote") if clean_text(tag.get_text(" "))]
    quoted = [clean_text(match) for match in re.findall(r"[“\"]([^”\"]{20,240})[”\"]", text)]
    attributions = re.findall(
        r"(?:—\s*[A-Z][\w .'-]{2,60}|\baccording to\s+[A-Z][\w .'-]{2,60}|\b[A-Z][\w .'-]{2,40}\s+said\b)",
        text,
    )
    return {
        "blockquote_count": len(blockquotes),
        "quoted_passage_count": len(quoted),
        "attribution_pattern_count": len(attributions),
        "attributed_quote_count": min(
            len(blockquotes) + len(quoted),
            len(attributions),
        ),
        "quote_snippets": (blockquotes + quoted)[:10],
        "attribution_snippets": [clean_text(value) for value in attributions[:10]],
    }


def extract_authorship(soup: BeautifulSoup, payloads: list) -> dict:
    author = (
        meta_content(soup, "author")
        or meta_property(soup, "article:author")
        or linked_author(soup)
        or json_ld_value(payloads, "author")
    )
    published = (
        meta_property(soup, "article:published_time")
        or meta_content(soup, "date")
        or json_ld_value(payloads, "datePublished")
    )
    modified = (
        meta_property(soup, "article:modified_time")
        or json_ld_value(payloads, "dateModified")
    )
    if not published:
        time_tag = soup.find("time", attrs={"datetime": True})
        published = time_tag.get("datetime") if time_tag else None
    return {
        "author_name": author,
        "published_date": published,
        "modified_date": modified,
    }


def extract_authority_evidence(text: str, authorship: dict, links: dict, schema_types: list[str]) -> dict:
    return {
        "named_author_present": bool(authorship["author_name"]),
        "organization_attribution_present": "Organization" in schema_types,
        "published_or_modified_date_present": bool(authorship["published_date"] or authorship["modified_date"]),
        "reference_like_link_count": len(links["reference_like_links"]),
        "methodology_language_count": len(METHODOLOGY_TERMS.findall(text)),
        "credentials_language_count": len(CREDENTIAL_TERMS.findall(text)),
    }


def extract_structural_readability(soup: BeautifulSoup, text: str, headings: dict) -> dict:
    sentences = [value for value in re.split(r"(?<=[.!?。！？])\s+", text) if value.strip()]
    sentence_lengths = [len(tokenize(value)) for value in sentences if tokenize(value)]
    paragraphs = [clean_text(tag.get_text(" ")) for tag in soup.find_all("p") if clean_text(tag.get_text(" "))]
    paragraph_lengths = [len(tokenize(value)) for value in paragraphs]
    word_count = len(tokenize(text))
    heading_count = sum(len(values) for values in headings.values())
    return {
        "sentence_count": len(sentence_lengths),
        "average_sentence_words": round(sum(sentence_lengths) / len(sentence_lengths), 1) if sentence_lengths else None,
        "average_paragraph_words": round(sum(paragraph_lengths) / len(paragraph_lengths), 1) if paragraph_lengths else None,
        "heading_count": heading_count,
        "headings_per_100_words": round(heading_count * 100 / word_count, 2) if word_count else None,
        "paragraph_count": len(paragraphs),
        "list_count": len(soup.find_all(["ul", "ol"])),
    }


def extract_term_evidence(*, body_text: str, emphasized_text: str) -> dict:
    tokens = [token for token in tokenize(body_text.lower()) if meaningful_token(token)]
    counts = Counter(tokens)
    emphasized = Counter(token for token in tokenize(emphasized_text.lower()) if meaningful_token(token))
    weighted = Counter(counts)
    for token, count in emphasized.items():
        weighted[token] += count * 3
    top_terms = [{"term": term, "count": counts[term]} for term, _ in weighted.most_common(12)]
    phrases = Counter(
        " ".join(tokens[index:index + 2])
        for index in range(max(len(tokens) - 1, 0))
    )
    repeated_phrases = [
        {"phrase": phrase, "count": count}
        for phrase, count in phrases.most_common(8)
        if count >= 2
    ]
    unique_count = len(set(tokens))
    return {
        "prominent_terms": [item["term"] for item in top_terms[:8]],
        "top_terms": top_terms,
        "repeated_phrases": repeated_phrases,
        "meaningful_token_count": len(tokens),
        "unique_token_count": unique_count,
        "lexical_diversity_ratio": round(unique_count / len(tokens), 4) if tokens else None,
        "top_term_concentration": round(counts.most_common(1)[0][1] / len(tokens), 4) if tokens else None,
    }


def aggregate_site_evidence(pages) -> dict:
    admitted = [
        page for page in pages
        if not getattr(page, "is_duplicate", False)
        and getattr(page, "word_count", 0) > 0
        and page_evidence(page)
    ]
    evidence = [page_evidence(page) for page in admitted]
    schema_counts = Counter(
        schema
        for item in evidence
        for schema in item.get("structured_data", {}).get("schema_types", [])
    )
    reference_domains = sorted({
        domain
        for item in evidence
        for domain in item.get("strategies", {}).get("citation", {}).get("distinct_reference_domains", [])
    })
    return {
        "analyzed_pages": len(admitted),
        "faq": {
            "pages_with_question_headings": count_pages(evidence, "faq", "question_heading_count"),
            "pages_with_qa_pairs": count_pages(evidence, "faq", "detected_qa_pair_count"),
            "pages_with_faq_schema": sum(bool(item.get("strategies", {}).get("faq", {}).get("faq_page_schema_present")) for item in evidence),
            "explanatory_pages_without_qa": sum(
                bool(strategy(item, "faq").get("explanatory_text_present"))
                and not strategy(item, "faq").get("detected_qa_pair_count")
                for item in evidence
            ),
        },
        "statistics": {
            "pages_with_numeric_claims": count_pages(evidence, "statistics", "numeric_claim_count"),
            "quantitative_statements": sum(strategy(item, "statistics").get("numeric_claim_count", 0) for item in evidence),
        },
        "citations": {
            "pages_with_reference_links": count_pages(evidence, "citation", "reference_like_link_count"),
            "reference_like_links": sum(strategy(item, "citation").get("reference_like_link_count", 0) for item in evidence),
            "distinct_reference_domains": reference_domains,
        },
        "authorship": {
            "pages_with_author": sum(bool(item.get("authorship", {}).get("author_name")) for item in evidence),
            "pages_with_dates": sum(bool(item.get("authorship", {}).get("published_date") or item.get("authorship", {}).get("modified_date")) for item in evidence),
        },
        "quotations": {
            "pages_with_quotations": sum(
                strategy(item, "quotation").get("blockquote_count", 0)
                + strategy(item, "quotation").get("quoted_passage_count", 0) > 0
                for item in evidence
            ),
        },
        "structured_data": dict(sorted(schema_counts.items())),
    }


def page_evidence(page) -> dict:
    return getattr(page, "evidence", None) or getattr(page, "evidence_json", None) or {}


def strategy(evidence: dict, name: str) -> dict:
    return evidence.get("strategies", {}).get(name, {})


def count_pages(evidence: list[dict], name: str, field: str) -> int:
    return sum(bool(strategy(item, name).get(field)) for item in evidence)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’-][^\W_]+)?", text, re.UNICODE)


def meaningful_token(token: str) -> bool:
    return len(token) >= 3 and token not in STOP_WORDS and not token.isdigit()


def snippets_for_matches(text: str, matches) -> list[str]:
    snippets = []
    for match in matches:
        start = max(0, match.start() - 70)
        end = min(len(text), match.end() + 70)
        snippet = clean_text(text[start:end])
        if snippet and snippet not in snippets:
            snippets.append(snippet)
    return snippets


def reference_phrase_snippets(text: str) -> list[str]:
    return snippets_for_matches(text, list(REFERENCE_TERMS.finditer(text)))[:10]


def glossary_definition_count(soup: BeautifulSoup, text: str) -> int:
    return len(soup.find_all("dt")) + len(re.findall(r"\b[A-Z][\w -]{2,40}\s+(?:means|refers to|is defined as)\b", text))


def json_ld_payloads(soup: BeautifulSoup) -> list:
    payloads = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payloads.append(json.loads(script.string or script.get_text(" ")))
        except (TypeError, ValueError):
            continue
    return payloads


def schema_type_set(payloads: list) -> set[str]:
    found: set[str] = set()
    for payload in payloads:
        collect_schema_types(payload, found)
    return found


def collect_schema_types(value, found: set[str]) -> None:
    if isinstance(value, dict):
        schema_type = value.get("@type")
        if isinstance(schema_type, str):
            found.add(schema_type)
        elif isinstance(schema_type, list):
            found.update(item for item in schema_type if isinstance(item, str))
        for child in value.values():
            collect_schema_types(child, found)
    elif isinstance(value, list):
        for child in value:
            collect_schema_types(child, found)


def json_ld_value(payloads: list, key: str) -> str | None:
    for payload in payloads:
        value = find_json_value(payload, key)
        if isinstance(value, str):
            return clean_text(value)
        if isinstance(value, dict):
            name = value.get("name")
            if isinstance(name, str):
                return clean_text(name)
        if isinstance(value, list):
            names = [item.get("name") for item in value if isinstance(item, dict) and isinstance(item.get("name"), str)]
            if names:
                return clean_text(", ".join(names))
    return None


def find_json_value(value, key: str):
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = find_json_value(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_json_value(child, key)
            if found is not None:
                return found
    return None


def meta_content(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": lambda value: isinstance(value, str) and value.lower() == name.lower()})
    return clean_text(tag.get("content")) if tag and tag.get("content") else None


def meta_property(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"property": name})
    return clean_text(tag.get("content")) if tag and tag.get("content") else None


def canonical_url(soup: BeautifulSoup, page_url: str) -> str | None:
    tag = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
    href = tag.get("href") if tag else None
    return urljoin(page_url, href.strip()) if isinstance(href, str) and href.strip() else None


def robots_directives(soup: BeautifulSoup) -> list[str]:
    values = []
    for name in ("robots", "googlebot"):
        value = meta_content(soup, name)
        if value:
            values.extend(item.strip().lower() for item in value.split(",") if item.strip())
    return list(dict.fromkeys(values))


def linked_author(soup: BeautifulSoup) -> str | None:
    tag = soup.find(attrs={"rel": lambda value: value and "author" in value})
    return clean_text(tag.get_text(" ")) if tag else None


def path_family(url: str) -> str:
    segments = [segment for segment in urlparse(url).path.split("/") if segment]
    if not segments:
        return "/"
    index = 1 if len(segments) > 1 and re.fullmatch(r"[a-zA-Z]{2}(?:-[a-zA-Z]{2})?", segments[0]) else 0
    return f"/{segments[index].lower()}"


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()
