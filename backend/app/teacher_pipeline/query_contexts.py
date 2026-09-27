"""Deterministic query-context preparation from stored Website Audit evidence."""

from dataclasses import dataclass
import re
from urllib.parse import urlparse


QUERY_POLICY_VERSION = "audit-evidence-contexts-v1"


@dataclass(frozen=True)
class QueryContext:
    query: str
    query_source: str
    query_intent: str
    target_url: str
    target_page_id: int | None
    originating_evidence: dict


class InsufficientQueryContexts(ValueError):
    pass


class AuditQueryContextGenerator:
    """Build diverse, deterministic queries without claiming observed search demand."""

    def generate(self, audit, *, count: int) -> list[QueryContext]:
        pages = [
            page for page in audit.pages
            if not page.is_duplicate
            and page.status_code is not None
            and 200 <= page.status_code < 300
            and page.word_count > 0
            and page.content_sha256
        ]
        pages.sort(key=lambda page: (self._family(page.url), page.url))
        candidates_by_page = [self._page_candidates(audit, page) for page in pages]
        selected: list[QueryContext] = []
        normalized_queries: list[set[str]] = []

        while len(selected) < count:
            added = False
            for candidates in candidates_by_page:
                while candidates:
                    candidate = candidates.pop(0)
                    tokens = self._tokens(candidate.query)
                    if not tokens or self._near_duplicate(tokens, normalized_queries):
                        continue
                    selected.append(candidate)
                    normalized_queries.append(tokens)
                    added = True
                    break
                if len(selected) == count:
                    break
            if not added:
                break

        if len(selected) < count:
            raise InsufficientQueryContexts(
                f"Audit evidence supports {len(selected)} distinct query contexts; "
                f"{count} were requested. Run a broader audit or lower the target."
            )
        return selected

    def _page_candidates(self, audit, page) -> list[QueryContext]:
        brand = (audit.property.brand_name or audit.property.name).strip()
        topics = self._topics(page)
        searchable = " ".join(filter(None, [page.url, page.page_title, page.h1, page.meta_description])).lower()
        templates = [
            ("informational", "What should someone know about {topic}?"),
            ("definition", "What is {topic}?"),
            ("factual_lookup", "Which facts explain {topic}?"),
        ]
        if any(term in searchable for term in ("guide", "how", "help", "steps", "tutorial")):
            templates.append(("how_to", "How can someone use {topic}?"))
        if any(term in searchable for term in ("compare", "comparison", " versus ", " vs ")):
            templates.append(("comparison", "How does {topic} compare with related options?"))
        if any(term in searchable for term in ("recommend", "best", "choose", "selection")):
            templates.append(("recommendation", "When should someone consider {topic}?"))
        if any(term in searchable for term in ("problem", "solution", "challenge", "fix")):
            templates.append(("problem_solution", "What problem does {topic} address?"))
        if any(term in searchable for term in ("product", "service", "feature", "platform", "software")):
            templates.append(("product_service_research", f"What does {brand} offer for {{topic}}?"))

        evidence = {
            "audit_id": audit.id,
            "page_id": page.id,
            "page_url": page.url,
            "page_title": page.page_title,
            "page_h1": page.h1,
            "page_meta_description": page.meta_description,
            "page_content_sha256": page.content_sha256,
            "path_family": self._family(page.url),
            "query_policy_version": QUERY_POLICY_VERSION,
        }
        return [
            QueryContext(
                query=template.format(topic=topic),
                query_source="generated",
                query_intent=intent,
                target_url=page.url,
                target_page_id=page.id,
                originating_evidence={**evidence, "topic": topic},
            )
            for topic in topics
            for intent, template in templates
        ]

    @staticmethod
    def _topics(page) -> list[str]:
        values = []
        for value in (page.h1, page.page_title, page.meta_description):
            cleaned = re.sub(r"\s+", " ", value or "").strip(" .!?-|—–:")
            if not cleaned:
                continue
            parts = re.split(r"\s+[|—–:]\s+|[.!?]", cleaned)
            for part in parts:
                words = part.strip().split()
                topic = " ".join(words[:14]).strip()
                if len(topic) >= 4 and topic.lower() not in {item.lower() for item in values}:
                    values.append(topic)
        return values

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", value.lower()))

    @staticmethod
    def _near_duplicate(tokens: set[str], existing: list[set[str]]) -> bool:
        for other in existing:
            union = tokens | other
            if union and len(tokens & other) / len(union) >= 0.88:
                return True
        return False

    @staticmethod
    def _family(url: str) -> str:
        segments = [part for part in urlparse(url).path.split("/") if part]
        return f"/{segments[0].lower()}" if segments else "/"
