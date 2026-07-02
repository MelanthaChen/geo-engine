from dataclasses import dataclass
from typing import Protocol


@dataclass
class RetrievedDocument:
    rank: int
    title: str
    url: str
    plain_text: str


class SearchProvider(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        ...
