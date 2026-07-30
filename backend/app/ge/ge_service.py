import random

from app.evaluation.evaluator import Evaluator
from app.ge.geo_rewriter import GeoRewriter
from app.ge.google_search_provider import GoogleSearchProvider
from app.ge.llm_runner import LLMRunner, OpenAILLMRunner
from app.ge.prompt_builder import PromptBuilder
from app.ge.search_provider import RetrievedDocument, SearchProvider


class GenerativeEngineService:
    PAPER_TOP_K = 5
    PAPER_RESPONSE_SAMPLES = 5
    PAPER_TOP_P = 1

    def __init__(
        self,
        search_provider: SearchProvider | None = None,
        llm_runner: LLMRunner | None = None,
        prompt_builder: PromptBuilder | None = None,
        evaluator: Evaluator | None = None,
    ):
        runner = llm_runner or OpenAILLMRunner()
        self.search_provider = search_provider or GoogleSearchProvider()
        self.rewriter = GeoRewriter(runner)
        self.llm_runner = runner
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.evaluator = evaluator or Evaluator()

    def run_query(
        self,
        query: str,
        strategies: list[str],
        model: str,
        temperature: float,
        random_seed: int,
        provider: str | None = None,
        retrieved_documents: list[RetrievedDocument] | None = None,
        on_strategy=None,
        on_sample=None,
    ) -> dict:
        runner = OpenAILLMRunner(provider) if provider else self.llm_runner
        rewriter = GeoRewriter(runner) if provider else self.rewriter
        documents = (
            retrieved_documents
            if retrieved_documents is not None
            else self.search_provider.search(query=query, top_k=self.PAPER_TOP_K)
        )

        if len(documents) < self.PAPER_TOP_K:
            source_name = "Uploaded dataset" if retrieved_documents is not None else "Google Search"
            raise RuntimeError(
                f"{source_name} returned {len(documents)} documents; "
                "the Princeton reproduction requires Top-5 results."
            )

        documents = sorted(documents, key=lambda document: document.rank)[
            : self.PAPER_TOP_K
        ]

        selected_document = random.Random(random_seed).choice(documents)
        strategy_outputs = []

        for strategy in strategies:
            if on_strategy:
                on_strategy(strategy)

            modified_document_text = rewriter.rewrite(
                document_text=selected_document.plain_text,
                query=query,
                strategy=strategy,
                model=model,
                temperature=temperature,
            )
            prompt = self.prompt_builder.build(
                query=query,
                documents=documents,
                selected_rank=selected_document.rank,
                modified_document_text=modified_document_text,
            )

            for sample_index in range(self.PAPER_RESPONSE_SAMPLES):
                if on_sample:
                    on_sample(
                        strategy,
                        sample_index + 1,
                        self.PAPER_RESPONSE_SAMPLES,
                    )

                # Appendix B.1 specifies five answer samples per method with
                # top_p=1. Temperature is passed through from the experiment
                # configuration, whose default is set to the paper value 0.7.
                answer = runner.generate(
                    system_prompt="",
                    user_prompt=prompt,
                    model=model,
                    temperature=temperature,
                    top_p=self.PAPER_TOP_P,
                )
                evaluation = self.evaluator.evaluate(
                    answer=answer,
                    selected_document_text=modified_document_text,
                    selected_title=selected_document.title,
                    selected_url=selected_document.url,
                    selected_rank=selected_document.rank,
                )
                strategy_outputs.append(
                    {
                        "strategy": strategy,
                        "sample_index": sample_index,
                        "modified_document_text": modified_document_text,
                        "prompt": prompt,
                        "answer": answer,
                        "evaluation": evaluation,
                    }
                )

        return {
            "query": query,
            "documents": documents,
            "selected_document_rank": selected_document.rank,
            "strategy_outputs": strategy_outputs,
        }
