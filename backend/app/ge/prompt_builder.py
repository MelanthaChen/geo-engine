from app.ge.search_provider import RetrievedDocument


GE_SYSTEM_PROMPT = (
    "Write an accurate and concise answer for the given user question, using "
    "_only_ the provided summarized web search results. The answer should be "
    "correct, high-quality, and written by an expert using an unbiased and "
    "journalistic tone. The user’s language of choice such as English, "
    "Francais, Espamol, Deutsch, or should be used. The answer should be "
    "informative, interesting, and engaging. The answer’s logic and reasoning "
    "should be rigorous and defensible.\n"
    "Every sentence in the answer should be _immediately followed_ by an "
    "in-line citation to the search result(s). The cited search result(s) "
    "should fully support _all_ the information in the sentence. Search "
    "results need to be cited using [index]. When citing several search "
    "results, use [1][2][3] format rather than [1, 2, 3]. You can use "
    "multiple search results to respond comprehensively while avoiding "
    "irrelevant search results."
)


class PromptBuilder:
    def build(
        self,
        query: str,
        documents: list[RetrievedDocument],
        selected_rank: int,
        modified_document_text: str,
    ) -> str:
        return (
            f"{GE_SYSTEM_PROMPT}\n\n"
            f"Question: {query}\n\n"
            "Search Results:\n"
            + self._source_text(
                documents=documents,
                selected_rank=selected_rank,
                modified_document_text=modified_document_text,
            )
        )

    def _source_text(
        self,
        documents: list[RetrievedDocument],
        selected_rank: int,
        modified_document_text: str,
    ) -> str:
        rows = []

        for document in documents:
            text = (
                modified_document_text
                if document.rank == selected_rank
                else document.plain_text
            )
            # The paper prompt references "summarized web search results", but
            # this project intentionally feeds cleaned full page text because
            # the user-specified reproduction variant has no stored summaries
            # and forbids summarization/chunking.
            rows.append(f"[{document.rank}] {text}")

        return "\n\n".join(rows)
