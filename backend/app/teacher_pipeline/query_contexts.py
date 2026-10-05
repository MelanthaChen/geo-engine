"""Deterministic query-context preparation from stored Website Audit evidence."""

from dataclasses import dataclass
import re
from urllib.parse import urlparse

from app.core.url_identity import canonical_url_identity


QUERY_POLICY_VERSION = "audit-evidence-contexts-v1"


@dataclass(frozen=True)
class QueryContext:
    query: str
    query_source: str
    query_intent: str
    target_url: str | None
    target_page_id: int | None
    originating_evidence: dict


class InsufficientQueryContexts(ValueError):
    pass


def resolve_audited_target(audit, query: str, candidates, recommendation=None):
    """Resolve a query's audited target without homepage or first-page fallback."""
    eligible = {
        canonical_url_identity(page.url): page
        for page in audit.pages
        if page.status_code == 200
        and not getattr(page, "is_duplicate", False)
        and (getattr(page, "word_count", 0) or 0) > 0
        and canonical_url_identity(page.url)
    }
    matches = [
        (candidate.rank, eligible[canonical_url_identity(candidate.url)])
        for candidate in candidates
        if canonical_url_identity(candidate.url) in eligible
    ]
    if matches:
        rank, page = min(matches, key=lambda item: item[0])
        return page, rank, "retrieved_by_provider"

    query_tokens = AuditQueryContextGenerator._tokens(query)
    best = None
    for page in eligible.values():
        page_tokens = AuditQueryContextGenerator._tokens(
            " ".join(filter(None, [getattr(page, "page_title", None), getattr(page, "h1", None), getattr(page, "meta_description", None)]))
        )
        overlap = len(query_tokens & page_tokens) / max(1, len(query_tokens))
        if overlap >= 0.1 and (best is None or overlap > best[0]):
            best = (overlap, page)
    if best:
        return best[1], None, "injected_for_controlled_experiment"
    return None, None, "content_gap"


class AuditQueryContextGenerator:
    """Build diverse, deterministic queries without claiming observed search demand."""

    def generate(self, audit, *, count: int) -> list[QueryContext]:
        candidates_by_page = [self._site_candidates(audit)]
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

    def _site_candidates(self, audit) -> list[QueryContext]:
        brand = (audit.property.brand_name or audit.property.name).strip()
        topics = self._site_topics(audit)
        searchable = " ".join(topics).lower()
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
            "page_id": None,
            "page_url": None,
            "site_topics": topics,
            "query_policy_version": QUERY_POLICY_VERSION,
        }
        return [
            QueryContext(
                query=template.format(topic=topic),
                query_source="generated",
                query_intent=intent,
                target_url=None,
                target_page_id=None,
                originating_evidence={**evidence, "topic": topic},
            )
            for topic in topics
            for intent, template in templates
        ]

    @staticmethod
    def _site_topics(audit) -> list[str]:
        values = []
        values.extend([audit.property.brand_name, audit.property.name, getattr(audit, "product_summary", None), getattr(audit, "brand_summary", None)])
        pages = [page for page in audit.pages if not getattr(page, "is_duplicate", False) and page.status_code and 200 <= page.status_code < 300 and (getattr(page, "word_count", 0) or 0) > 0]
        for page in pages:
            values.extend((page.h1, page.page_title))
        topics = []
        for value in values:
            cleaned = re.sub(r"\s+", " ", value or "").strip(" .!?-|—–:")
            if not cleaned:
                continue
            parts = re.split(r"\s+[|—–:]\s+|[.!?]", cleaned)
            for part in parts:
                words = part.strip().split()
                topic = " ".join(words[:14]).strip()
                if len(topic) >= 4 and topic.lower() not in {item.lower() for item in topics}:
                    topics.append(topic)
        return topics

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
