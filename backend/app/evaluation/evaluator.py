import math
import re
from dataclasses import dataclass


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
        selected_rank: int,
    ) -> EvaluationResult:
        cited_sentences = self._sentences_with_citations(answer)
        total_words = sum(len(self._words(sentence)) for sentence, _ in cited_sentences)
        selected_sentence_records = [
            (sentence, citations)
            for sentence, citations in cited_sentences
            if selected_rank in citations
        ]

        shared_word_count = 0.0
        citation_positions = []

        for index, (sentence, citations) in enumerate(
            selected_sentence_records,
            start=1,
        ):
            citation_positions.append(index)
            # Section 2.2.1 states that a sentence cited by multiple sources
            # shares word count among those sources. The exact tokenization is
            # not specified, so this approximation uses regex word tokens.
            shared_word_count += len(self._words(sentence)) / max(len(citations), 1)

        normalized_word_count = (
            shared_word_count / total_words
            if total_words > 0
            else 0.0
        )
        position = min(citation_positions) if citation_positions else None
        position_adjustment = (
            1 / math.exp(position - 1)
            if position is not None
            else 0.0
        )
        pawc = normalized_word_count * position_adjustment

        return EvaluationResult(
            word_count=round(shared_word_count),
            position=position,
            pawc=round(pawc, 6),
            citation_count=len(selected_sentence_records),
            # The paper reports Position-Adjusted Word Count as one objective
            # impression metric. We expose it as visibility_score here because
            # the UI needs one scalar comparison column.
            visibility_score=round(pawc, 6),
        )

    def _sentences_with_citations(self, answer: str) -> list[tuple[str, set[int]]]:
        sentence_candidates = re.split(r"(?<=[.!?])\s+", answer or "")
        rows = []

        for sentence in sentence_candidates:
            citations = {
                int(match)
                for match in re.findall(r"\[(\d+)\]", sentence)
            }

            if citations:
                rows.append((sentence, citations))

        return rows

    def _words(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z0-9'-]*", text or "")
