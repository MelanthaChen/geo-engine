from app.ge.search_provider import RetrievedDocument


class PromptBuilder:
    def build(
        self,
        query: str,
        documents: list[RetrievedDocument],
        selected_rank: int,
        modified_document_text: str,
    ) -> str:
        document_blocks = []

        for document in documents:
            text = (
                modified_document_text
                if document.rank == selected_rank
                else document.plain_text
            )
            document_blocks.append(
                "\n".join(
                    [
                        f"Document {document.rank}",
                        f"Title: {document.title}",
                        f"URL: {document.url}",
                        "Text:",
                        text,
                    ]
                )
            )

        return (
            "Answer the question using the complete text of the retrieved "
            "documents below. Cite or mention sources when useful.\n\n"
            f"Question:\n{query}\n\n"
            "Retrieved documents:\n\n"
            + "\n\n---\n\n".join(document_blocks)
        )
