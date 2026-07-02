from app.ge.llm_runner import LLMRunner


STRATEGY_LABELS = {
    "original": "Original",
    "statistics": "Statistics Addition",
    "citation": "Citation Addition",
    "quotation": "Quotation Addition",
    "authoritative": "Authoritative",
    "easy_to_understand": "Easy-to-understand",
    "fluency": "Fluency Optimization",
    "unique_words": "Unique Words",
    "technical_terms": "Technical Terms",
    "keyword_stuffing": "Keyword Stuffing",
}


STRATEGY_INSTRUCTIONS = {
    "statistics": (
        "Modify the document by adding relevant quantitative statistics where "
        "they strengthen existing claims. Do not invent facts that conflict "
        "with the document."
    ),
    "citation": (
        "Modify the document by adding citation-style references and source "
        "attribution around existing factual claims."
    ),
    "quotation": (
        "Modify the document by adding short quotation-style authoritative "
        "statements that support existing points."
    ),
    "authoritative": (
        "Rewrite the document in a more authoritative style while preserving "
        "its meaning, claims, and scope."
    ),
    "easy_to_understand": (
        "Rewrite the document to be easier to understand, using clearer "
        "sentence structure without removing substance."
    ),
    "fluency": (
        "Improve fluency, transitions, and readability while preserving the "
        "document's claims and details."
    ),
    "unique_words": (
        "Increase lexical variety by using distinctive but natural wording. "
        "Do not alter the document's factual content."
    ),
    "technical_terms": (
        "Add appropriate technical terminology where it clarifies the topic. "
        "Do not add unsupported concepts."
    ),
    "keyword_stuffing": (
        "Add repeated query-relevant keywords in a mechanically optimized way "
        "while keeping the document readable enough for an experiment."
    ),
}


class GeoRewriter:
    def __init__(self, llm_runner: LLMRunner):
        self.llm_runner = llm_runner

    def rewrite(
        self,
        document_text: str,
        query: str,
        strategy: str,
        model: str,
        temperature: float,
    ) -> str:
        if strategy == "original":
            return document_text

        instruction = STRATEGY_INSTRUCTIONS[strategy]

        prompt = (
            "You are reproducing an academic Generative Engine Optimization "
            "experiment. Modify only the provided source document according "
            "to the named strategy. Return only the modified document text.\n\n"
            f"Query:\n{query}\n\n"
            f"Strategy:\n{STRATEGY_LABELS[strategy]}\n\n"
            f"Instruction:\n{instruction}\n\n"
            f"Source document:\n{document_text}"
        )

        return self.llm_runner.generate(
            system_prompt=(
                "You rewrite one retrieved web document for a controlled GEO "
                "experiment. Preserve the document's topic and factual scope."
            ),
            user_prompt=prompt,
            model=model,
            temperature=temperature,
        )
