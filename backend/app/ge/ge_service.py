import random
import time

from app.ge.geo_rewriter import GeoRewriter
from app.ge.search_provider_factory import build_search_provider
from app.ge.llm_runner import LLMRunner, OpenAILLMRunner
from app.ge.prompt_builder import PromptBuilder
from app.ge.search_provider import RetrievedDocument, SearchProvider


class GenerativeEngineService:
    PAPER_TOP_K = 5
    PAPER_RESPONSE_SAMPLES = 5
    PAPER_TOP_P = 1

    LIVE_TARGET_SOURCE_CHARS = 6000
    LIVE_REFERENCE_SOURCE_CHARS = 4500
    LIVE_ANSWER_MAX_TOKENS = 1024

    def __init__(
        self,
        search_provider: SearchProvider | None = None,
        llm_runner: LLMRunner | None = None,
        prompt_builder: PromptBuilder | None = None,
    ):
        runner = llm_runner or OpenAILLMRunner()
        self.search_provider = search_provider or build_search_provider()
        self.rewriter = GeoRewriter(runner)
        self.llm_runner = runner
        self.prompt_builder = prompt_builder or PromptBuilder()

    def run_query(
        self,
        query: str,
        strategies: list[str],
        model: str,
        temperature: float,
        random_seed: int,
        provider: str | None = None,
        retrieved_documents: list[RetrievedDocument] | None = None,
        response_samples: int | None = None,
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
            source_name = "Uploaded dataset" if retrieved_documents is not None else "Live Retrieval"
            raise RuntimeError(
                f"{source_name} returned {len(documents)} documents; "
                "the Princeton reproduction requires Top-5 results."
            )

        documents = sorted(documents, key=lambda document: document.rank)[
            : self.PAPER_TOP_K
        ]

        official_target = next(
            (document for document in documents if document.is_optimization_target),
            None,
        )
        # GEO-bench publishes the randomly selected source as zero-based
        # sugg_idx. It must remain fixed across methods and repeated runs.
        selected_document = official_target or random.Random(random_seed).choice(documents)
        strategy_outputs = []

        sample_count = response_samples or self.PAPER_RESPONSE_SAMPLES
        for strategy in strategies:
            if on_strategy:
                on_strategy(strategy)

            rewrite_artifact = rewriter.rewrite_artifact(
                document_text=selected_document.plain_text,
                query=query,
                strategy=strategy,
                model=model,
                temperature=temperature,
            )
            modified_document_text = rewrite_artifact.document
            prompt = self.prompt_builder.build(
                query=query,
                documents=documents,
                selected_rank=selected_document.rank,
                modified_document_text=modified_document_text,
            )

            for sample_index in range(sample_count):
                if on_sample:
                    on_sample(
                        strategy,
                        sample_index + 1,
                        sample_count,
                    )

                # Paper-mode and historical experiments retain the five-sample
                # default. Dataset generation passes repetitions per context
                # explicitly so repetition count cannot masquerade as context
                # count. top_p and temperature behavior are unchanged.
                started_at = time.perf_counter()
                answer = runner.generate(
                    system_prompt="",
                    user_prompt=prompt,
                    model=model,
                    temperature=temperature,
                    top_p=self.PAPER_TOP_P,
                )
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                strategy_outputs.append(
                    {
                        "strategy": strategy,
                        "query": query,
                        "sample_index": sample_index,
                        "modified_document_text": modified_document_text,
                        "rewrite_plan": rewrite_artifact.plan,
                        "prompt": prompt,
                        "answer": answer,
                        "latency_ms": latency_ms,
                    }
                )

        return {
            "query": query,
            "documents": documents,
            "selected_document_rank": selected_document.rank,
            "selected_document": selected_document,
            "strategy_outputs": strategy_outputs,
        }
