import math
import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class EvaluationResult:
    word_count: int
    position: int | None
    pawc: float
    citation_count: int
    visibility_score: float


class Evaluator:
    def evaluate(
        self,
        answer: str,
        selected_document_text: str,
        selected_title: str,
        selected_url: str,
    ) -> EvaluationResult:
        answer_words = self._words(answer)
        source_words = set(self._words(selected_document_text))
        overlap_count = sum(1 for word in answer_words if word in source_words)
        position = self._first_source_position(
            answer=answer,
            selected_title=selected_title,
            selected_url=selected_url,
        )
        adjusted_position = position if position is not None else len(answer_words)
        pawc = (
            overlap_count / math.log2(adjusted_position + 2)
            if adjusted_position >= 0
            else 0
        )
        citation_count = self._citation_count(
            answer=answer,
            selected_title=selected_title,
            selected_url=selected_url,
        )
        visibility_score = round(pawc + (citation_count * 10), 3)

        return EvaluationResult(
            word_count=overlap_count,
            position=position,
            pawc=round(pawc, 3),
            citation_count=citation_count,
            visibility_score=visibility_score,
        )

    def _words(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z0-9'-]*", (text or "").lower())

    def _first_source_position(
        self,
        answer: str,
        selected_title: str,
        selected_url: str,
    ) -> int | None:
        lowered = answer.lower()
        candidates = self._source_markers(selected_title, selected_url)
        positions = [
            len(self._words(answer[:index]))
            for marker in candidates
            if (index := lowered.find(marker)) >= 0
        ]

        return min(positions) if positions else None

    def _citation_count(
        self,
        answer: str,
        selected_title: str,
        selected_url: str,
    ) -> int:
        lowered = answer.lower()
        return sum(
            lowered.count(marker)
            for marker in self._source_markers(selected_title, selected_url)
        )

    def _source_markers(
        self,
        selected_title: str,
        selected_url: str,
    ) -> list[str]:
        parsed = urlparse(selected_url)
        domain = parsed.netloc.lower().removeprefix("www.")
        title = (selected_title or "").lower().strip()

        return [
            marker
            for marker in [domain, selected_url.lower(), title]
            if marker
        ]
