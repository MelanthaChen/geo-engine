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
        on_strategy=None,
        on_sample=None,
    ) -> dict:
        documents = self.search_provider.search(query=query, top_k=self.PAPER_TOP_K)

        if len(documents) < self.PAPER_TOP_K:
            raise RuntimeError(
                f"Google Search returned {len(documents)} documents; "
                "the Princeton reproduction requires Top-5 results."
            )

        selected_document = random.Random(random_seed).choice(documents)
        strategy_outputs = []

        for strategy in strategies:
            if on_strategy:
                on_strategy(strategy)

            modified_document_text = self.rewriter.rewrite(
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
                answer = self.llm_runner.generate(
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
