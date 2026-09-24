from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


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


class SearchProvider(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        ...
