from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import urlparse


@dataclass
class RetrievedDocument:
    rank: int
    title: str
    url: str
    plain_text: str
    is_optimization_target: bool = False
    source_role: str | None = None
    retrieval_provider: str | None = None
    retrieved_at: datetime | None = None
    content_sha256: str | None = None
    query_policy_version: str | None = None
    source_audit_id: int | None = None
    supporting_evidence: dict | None = None
    snippet: str | None = None
    provider_metadata: dict | None = None


class SearchProviderError(RuntimeError):
    """A provider-neutral live retrieval failure safe to expose to API clients."""


class SearchProvider(Protocol):
    provider_id: str
    display_name: str

    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        ...


def provider_id(provider: SearchProvider, documents: list[RetrievedDocument]) -> str:
    return (
        getattr(provider, "provider_id", None)
        or next((item.retrieval_provider for item in documents if item.retrieval_provider), None)
        or "unknown"
    )


def target_retrieval_status(
    target_url: str,
    results: list[RetrievedDocument],
) -> str:
    target_identity = _url_identity(target_url)
    if any(_url_identity(result.url) == target_identity for result in results):
        return "retrieved_by_provider"
    return "injected_for_controlled_experiment"


def retrieval_result_ledger(results: list[RetrievedDocument]) -> list[dict]:
    return [
        {
            "rank": result.rank,
            "title": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "provider_metadata": result.provider_metadata,
        }
        for result in results
    ]


def _url_identity(url: str) -> tuple[str, str]:
    parsed = urlparse(url.strip() if "://" in url else f"https://{url.strip()}")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    return host, path
