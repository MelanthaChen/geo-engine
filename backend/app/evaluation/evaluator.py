import itertools
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


def get_num_words(line: list[str]) -> int:
    """Official GEO helper: count tokenized words longer than two chars."""

    return len([word for word in line if len(word) > 2])


def extract_citations_new(text: str):
    """Port of GEO-optim/GEO/src/utils.py::extract_citations_new."""

    def ecn(sentence: str) -> list[int]:
        citation_pattern = r"\[[^\w\s]*\d+[^\w\s]*\]"
        return [
            int(re.findall(r"\d+", citation)[0])
            for citation in re.findall(citation_pattern, sentence)
        ]

    paragraphs = re.split(r"\n\n", text or "")
    sentences = [_sent_tokenize(paragraph) for paragraph in paragraphs]
    return [
        [
            (
                _word_tokenize(sentence),
                sentence,
                ecn(sentence),
            )
            for sentence in paragraph_sentences
        ]
        for paragraph_sentences in sentences
    ]


def impression_wordpos_count_simple(sentences, n: int = 5, normalize: bool = True):
    """Port of GEO-optim/GEO/src/utils.py::impression_wordpos_count_simple."""

    flattened_sentences = list(itertools.chain(*sentences))
    scores = [0 for _ in range(n)]

    for index, sentence in enumerate(flattened_sentences):
        for citation in sentence[2]:
            score = get_num_words(sentence[0])
            score *= (
                math.exp(-1 * index / (len(flattened_sentences) - 1))
                if len(flattened_sentences) > 1
                else 1
            )
            score /= len(sentence[2])

            try:
                scores[citation - 1] += score
            except Exception:
                print(f"Citation Hallucinated: {citation}")

    return _normalize_scores(scores, n, normalize)


def impression_word_count_simple(sentences, n: int = 5, normalize: bool = True):
    """Port of GEO-optim/GEO/src/utils.py::impression_word_count_simple."""

    flattened_sentences = list(itertools.chain(*sentences))
    scores = [0 for _ in range(n)]

    for _, sentence in enumerate(flattened_sentences):
        for citation in sentence[2]:
            score = get_num_words(sentence[0])
            score /= len(sentence[2])

            try:
                scores[citation - 1] += score
            except Exception:
                print(f"Citation Hallucinated: {citation}")

    return _normalize_scores(scores, n, normalize)


def impression_pos_count_simple(sentences, n: int = 5, normalize: bool = True):
    """Port of GEO-optim/GEO/src/utils.py::impression_pos_count_simple."""

    flattened_sentences = list(itertools.chain(*sentences))
    scores = [0 for _ in range(n)]

    for index, sentence in enumerate(flattened_sentences):
        for citation in sentence[2]:
            score = 1
            score *= (
                math.exp(-1 * index / (len(flattened_sentences) - 1))
                if len(flattened_sentences) > 1
                else 1
            )
            score /= len(sentence[2])

            try:
                scores[citation - 1] += score
            except Exception:
                print(f"Citation Hallucinated: {citation}")

    return _normalize_scores(scores, n, normalize)


def _normalize_scores(scores: list[float], n: int, normalize: bool):
    if normalize and sum(scores) != 0:
        return [score / sum(scores) for score in scores]

    if normalize:
        return [1 / n for _ in range(n)]

    return scores


def _sent_tokenize(paragraph: str) -> list[str]:
    try:
        import nltk

        return nltk.sent_tokenize(paragraph)
    except Exception:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph or "")
            if sentence.strip()
        ]


def _word_tokenize(sentence: str) -> list[str]:
    try:
        import nltk

        return nltk.word_tokenize(sentence)
    except Exception:
        return re.findall(r"\w+|[^\w\s]", sentence or "", flags=re.UNICODE)


class Evaluator:
    def evaluate(
        self,
        answer: str,
        selected_document_text: str,
        selected_title: str,
        selected_url: str,
        selected_rank: int,
    ) -> EvaluationResult:
        sentences = extract_citations_new(answer)
        source_count = 5
        selected_index = selected_rank - 1

        wordpos_scores = impression_wordpos_count_simple(
            sentences,
            source_count,
            normalize=True,
        )
        raw_word_scores = impression_word_count_simple(
            sentences,
            source_count,
            normalize=False,
        )
        citation_count, position = self._selected_citation_stats(
            sentences,
            selected_rank,
        )
        selected_pawc = self._score_for_selected_source(
            wordpos_scores,
            selected_index,
        )
        selected_word_count = self._score_for_selected_source(
            raw_word_scores,
            selected_index,
        )

        return EvaluationResult(
            word_count=round(selected_word_count),
            position=position,
            pawc=round(selected_pawc, 6),
            citation_count=citation_count,
            visibility_score=round(selected_pawc, 6),
        )

    def _score_for_selected_source(
        self,
        scores: list[float],
        selected_index: int,
    ) -> float:
        if 0 <= selected_index < len(scores):
            return scores[selected_index]

        return 0.0

    def _selected_citation_stats(
        self,
        sentences,
        selected_rank: int,
    ) -> tuple[int, int | None]:
        citation_count = 0
        first_position = None

        for position, sentence in enumerate(itertools.chain(*sentences), start=1):
            selected_occurrences = [
                citation for citation in sentence[2] if citation == selected_rank
            ]

            if selected_occurrences and first_position is None:
                first_position = position

            citation_count += len(selected_occurrences)

        return citation_count, first_position
