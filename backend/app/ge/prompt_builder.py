import re

from app.ge.search_provider import RetrievedDocument


GE_SYSTEM_PROMPT = """Write an accurate and concise answer for the given user question, using _only_ the provided summarized web search results. The answer should be correct, high-quality, and written by an expert using an unbiased and journalistic tone. The user's language of choice such as English, Français, Español, Deutsch, or 日本語 should be used. The answer should be informative, interesting, and engaging. The answer's logic and reasoning should be rigorous and defensible. Every sentence in the answer should be _immediately followed_ by an in-line citation to the search result(s). The cited search result(s) should fully support _all_ the information in the sentence. Search results need to be cited using [index]. When citing several search results, use [1][2][3] format rather than [1, 2, 3]. You can use multiple search results to respond comprehensively while avoiding irrelevant search results."""


class PromptBuilder:
    def build(
        self,
        query: str,
        documents: list[RetrievedDocument],
        selected_rank: int,
        modified_document_text: str,
        source_char_limits: dict[int, int] | None = None,
    ) -> str:
        return (
            f"{GE_SYSTEM_PROMPT}\n\n"
            f"Question: {query}\n\n"
            "Search Results:\n"
            + self._source_text(
                query=query,
                documents=documents,
                selected_rank=selected_rank,
                modified_document_text=modified_document_text,
                source_char_limits=source_char_limits,
            )
            + "\n"
        )

    def _source_text(
        self,
        query: str,
        documents: list[RetrievedDocument],
        selected_rank: int,
        modified_document_text: str,
        source_char_limits: dict[int, int] | None = None,
    ) -> str:
        rows = []

        for document in documents:
            text = (
                modified_document_text
                if document.rank == selected_rank
                else document.plain_text
            )

            # Official replication callers do not pass source_char_limits,
            # preserving the historical full-text prompt behavior.
            #
            # Live/new-website Teacher Validation passes deterministic source
            # budgets so large retrieved pages cannot exceed the model context.
            if source_char_limits is not None:
                limit = source_char_limits.get(document.rank)
                if limit is not None and limit > 0:
                    text = self._select_relevant_text(
                        text=text,
                        query=query,
                        max_chars=limit,
                    )

            rows.append(
                f"### Source {document.rank}:\n{text}\n\n\n"
            )

        return "\n\n".join(rows)

    @staticmethod
    def _select_relevant_text(
        *,
        text: str,
        query: str,
        max_chars: int,
    ) -> str:
        """
        Deterministically reduce one source for model input only.

        The original RetrievedDocument/plain-text snapshot remains untouched.
        Preference is given to paragraphs containing query terms, and selected
        paragraphs are restored to their original document order.
        """
        text = (text or "").strip()

        if len(text) <= max_chars:
            return text

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n+", text)
            if paragraph.strip()
        ]

        if not paragraphs:
            return text[:max_chars]

        query_terms = {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", query)
            if len(token) >= 3
        }

        scored: list[tuple[int, int, str]] = []

        for index, paragraph in enumerate(paragraphs):
            lower = paragraph.lower()
            overlap = sum(
                1 for term in query_terms
                if term in lower
            )

            scored.append((overlap, index, paragraph))

        # Highest query overlap first; ties prefer earlier source paragraphs.
        scored.sort(key=lambda item: (-item[0], item[1]))

        selected: list[tuple[int, str]] = []
        used = 0

        for _, index, paragraph in scored:
            remaining = max_chars - used

            if remaining <= 0:
                break

            separator_cost = 2 if selected else 0

            if len(paragraph) + separator_cost <= remaining:
                selected.append((index, paragraph))
                used += len(paragraph) + separator_cost
                continue

            # If nothing has fit yet, keep a bounded part of the best paragraph
            # instead of returning an empty source.
            if not selected and remaining > 0:
                selected.append((index, paragraph[:remaining]))
                used = max_chars

            break

        if not selected:
            return text[:max_chars]

        # Preserve original document order in the final prompt.
        selected.sort(key=lambda item: item[0])

        return "\n\n".join(
            paragraph for _, paragraph in selected
        )[:max_chars]
