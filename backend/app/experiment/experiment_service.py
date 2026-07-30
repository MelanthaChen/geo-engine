import json
from typing import Any

from app.experiment.geo_bench_loader import GeoBenchLoader
from app.ge.ge_service import GenerativeEngineService
from app.ge.geo_rewriter import STRATEGY_LABELS
from app.ge.search_provider import RetrievedDocument
from app.core.llm_provider import normalize_llm_provider
from app.models.experiment import Experiment
from app.storage.experiment_repository import ExperimentRepository


CUSTOM_BENCHMARK_QUERIES = [
    "What is generative engine optimization?",
    "How do AI search engines decide which sources to cite?",
    "Which content strategies improve visibility in AI-generated answers?",
    "How are citations evaluated in generative search results?",
    "What makes a source authoritative for an LLM answer?",
    "How does adding statistics affect content visibility in generative engines?",
    "Can keyword stuffing improve visibility in AI answers?",
    "Why does source position matter in generated answers?",
    "How should content be rewritten for generative search experiments?",
    "What is position-adjusted word count in GEO evaluation?",
]

PAPER_MODE_SEED_COUNT = 5


class ExperimentService:
    def __init__(
        self,
        repository: ExperimentRepository,
        ge_service: GenerativeEngineService | None = None,
        geo_bench_loader: GeoBenchLoader | None = None,
    ):
        self.repository = repository
        self.ge_service = ge_service or GenerativeEngineService()
        self.geo_bench_loader = geo_bench_loader or GeoBenchLoader()

    def run_experiment(
        self,
        *,
        property_id: int | None,
        campaign_id: int | None = None,
        name: str,
        description: str | None,
        llm_model: str,
        provider: str | None = None,
        dataset_name: str,
        strategies: list[str],
        metrics: list[str],
        number_of_queries: int,
        random_seed: int,
        temperature: float,
        queries: list[str] | None = None,
        dataset_documents: list[dict[str, Any]] | None = None,
    ) -> dict:
        self._validate_strategies(strategies)
        strategies = self._paper_mode_strategies(dataset_name, strategies)
        experiment = self.create_experiment(
            property_id=property_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
            llm_model=llm_model,
            provider=provider,
            dataset_name=dataset_name,
            queries=queries,
            strategies=strategies,
            metrics=metrics,
            number_of_queries=number_of_queries,
            random_seed=random_seed,
            temperature=temperature,
            dataset_documents=dataset_documents,
        )
        self.execute_experiment(experiment.id)
        return self.repository.serialize(experiment)

    def create_experiment(
        self,
        *,
        property_id: int | None,
        campaign_id: int | None = None,
        name: str,
        description: str | None,
        llm_model: str,
        provider: str | None = None,
        dataset_name: str,
        strategies: list[str],
        metrics: list[str],
        number_of_queries: int,
        random_seed: int,
        temperature: float,
        queries: list[str] | None = None,
        dataset_documents: list[dict[str, Any]] | None = None,
    ) -> Experiment:
        self._validate_strategies(strategies)
        strategies = self._paper_mode_strategies(dataset_name, strategies)
        benchmark_input = self._build_benchmark_input(
            number_of_queries,
            dataset_name,
            queries,
            dataset_documents,
        )
        query_plan, _ = self._load_query_plan(number_of_queries, benchmark_input)
        execution_count = self._execution_count(dataset_name, len(query_plan))

        return self.repository.create_run(
            property_id=property_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
            llm_model=llm_model,
            provider=normalize_llm_provider(provider),
            dataset_name=dataset_name,
            benchmark_queries=benchmark_input,
            strategies=strategies,
            metrics=metrics,
            number_of_queries=execution_count,
            random_seed=random_seed,
            temperature=temperature,
        )

    def execute_experiment(self, experiment_id: int) -> Experiment:
        experiment = self.repository.get_run(experiment_id)

        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        strategies = json.loads(experiment.strategies_json or "[]")
        queries, uploaded_documents_by_query = self._load_query_plan(
            experiment.number_of_queries or 1,
            json.loads(experiment.benchmark_queries_json or "[]"),
        )

        try:
            self.repository.mark_running(experiment)

            completed_runs = 0

            for index, query in enumerate(queries):
                seed_values = self._seed_values(
                    experiment.dataset_name or "",
                    experiment.random_seed or 0,
                    index,
                )

                for seed_value in seed_values:
                    completed_runs = self._execute_query_seed(
                        experiment=experiment,
                        query=query,
                        seed_value=seed_value,
                        completed_runs=completed_runs,
                        strategies=strategies,
                        uploaded_documents=uploaded_documents_by_query.get(query),
                    )

            self.repository.mark_completed(experiment)
        except Exception as exc:
            self.repository.mark_failed(experiment, str(exc))

        return experiment

    def _execute_query_seed(
        self,
        *,
        experiment: Experiment,
        query: str,
        seed_value: int,
        completed_runs: int,
        strategies: list[str],
        uploaded_documents: list[RetrievedDocument] | None,
    ) -> int:
        self.repository.update_progress(
            experiment,
            current_query=query,
            current_strategy=strategies[0],
            completed_queries=completed_runs,
        )
        result = self.ge_service.run_query(
            query=query,
            strategies=strategies,
            model=experiment.llm_model or "gpt-3.5-turbo",
            temperature=experiment.temperature or 0.7,
            random_seed=seed_value,
            retrieved_documents=uploaded_documents,
            on_strategy=lambda strategy, current_query=query: (
                self.repository.update_current_strategy(
                    experiment,
                    current_query=current_query,
                    current_strategy=strategy,
                )
            ),
            on_sample=(
                lambda strategy, sample, total, current_query=query: (
                    self.repository.update_current_strategy(
                        experiment,
                        current_query=current_query,
                        current_strategy=strategy,
                        current_sample=sample,
                    )
                )
            ),
        )
        self.repository.store_query_run(
            experiment,
            query=query,
            seed_value=seed_value,
            documents=result["documents"],
            selected_document_rank=result["selected_document_rank"],
            strategy_outputs=result["strategy_outputs"],
        )

        return completed_runs + 1

    def _seed_values(
        self,
        dataset_name: str,
        random_seed: int,
        query_index: int,
    ) -> list[int]:
        if dataset_name == "geo_bench":
            # The paper reports five random seeds but does not publish their
            # exact numeric values, so Paper Mode derives a deterministic
            # five-seed set from the configured base seed.
            return [
                random_seed + seed_offset
                for seed_offset in range(PAPER_MODE_SEED_COUNT)
            ]

        return [random_seed + query_index]

    def _execution_count(self, dataset_name: str, query_count: int) -> int:
        if dataset_name == "geo_bench":
            return query_count * PAPER_MODE_SEED_COUNT

        return query_count

    def _paper_mode_strategies(
        self,
        dataset_name: str,
        strategies: list[str],
    ) -> list[str]:
        if dataset_name != "geo_bench" or "original" in strategies:
            return strategies

        return ["original", *strategies]

    def _build_benchmark_input(
        self,
        number_of_queries: int,
        dataset_name: str,
        queries: list[str] | None = None,
        dataset_documents: list[dict[str, Any]] | None = None,
    ) -> list[Any]:
        if dataset_documents:
            return self._build_uploaded_dataset_entries(
                number_of_queries,
                dataset_documents,
            )

        if dataset_name == "geo_bench":
            return self.geo_bench_loader.load_test_entries(
                max(1, number_of_queries),
            )

        if queries:
            cleaned_queries = [
                query.strip()
                for query in queries
                if query and query.strip()
            ]

            return cleaned_queries[: max(1, number_of_queries)]

        limit = max(1, min(number_of_queries, len(CUSTOM_BENCHMARK_QUERIES)))
        return CUSTOM_BENCHMARK_QUERIES[:limit]

    def _load_query_plan(
        self,
        number_of_queries: int,
        benchmark_input: list[Any] | None = None,
    ) -> tuple[list[str], dict[str, list[RetrievedDocument]]]:
        if benchmark_input and all(
            isinstance(item, dict) and "documents" in item
            for item in benchmark_input
        ):
            queries = []
            documents_by_query = {}

            for item in benchmark_input[: max(1, number_of_queries)]:
                query = str(item.get("query") or "").strip()

                if not query:
                    continue

                queries.append(query)
                documents_by_query[query] = self._documents_from_uploaded_entry(item)

            return queries, documents_by_query

        return (
            self._load_queries_from_strings(number_of_queries, benchmark_input),
            {},
        )

    def _load_queries_from_strings(
        self,
        number_of_queries: int,
        queries: list[Any] | None = None,
    ) -> list[str]:
        if queries:
            cleaned_queries = [
                str(query).strip()
                for query in queries
                if isinstance(query, str) and query.strip()
            ]

            return cleaned_queries[: max(1, number_of_queries)]

        limit = max(1, min(number_of_queries, len(CUSTOM_BENCHMARK_QUERIES)))
        return CUSTOM_BENCHMARK_QUERIES[:limit]

    def _build_uploaded_dataset_entries(
        self,
        number_of_queries: int,
        dataset_documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        query_order = []

        for row in dataset_documents:
            query = str(row.get("query") or "").strip()
            content = str(row.get("content") or "").strip()

            if not query or not content:
                continue

            if query not in grouped:
                grouped[query] = []
                query_order.append(query)

            grouped[query].append(
                {
                    "rank": int(row.get("rank") or len(grouped[query]) + 1),
                    "title": str(row.get("title") or "").strip(),
                    "url": str(row.get("url") or "").strip(),
                    "content": content,
                }
            )

        entries = []

        for query in query_order[: max(1, number_of_queries)]:
            documents = sorted(
                grouped[query],
                key=lambda document: document["rank"],
            )

            if len(documents) < GenerativeEngineService.PAPER_TOP_K:
                raise ValueError(
                    f"Uploaded dataset query {query!r} has {len(documents)} "
                    "documents; the Princeton reproduction requires exactly "
                    "five ranked documents per query."
                )

            entries.append(
                {
                    "query": query,
                    "documents": documents[: GenerativeEngineService.PAPER_TOP_K],
                }
            )

        if not entries:
            raise ValueError(
                "Uploaded dataset did not contain any valid query/document rows."
            )

        return entries

    def _documents_from_uploaded_entry(
        self,
        entry: dict[str, Any],
    ) -> list[RetrievedDocument]:
        documents = []

        for document in entry.get("documents") or []:
            documents.append(
                RetrievedDocument(
                    rank=int(document.get("rank") or len(documents) + 1),
                    title=str(document.get("title") or ""),
                    url=str(document.get("url") or ""),
                    plain_text=str(document.get("content") or ""),
                )
            )

        return sorted(documents, key=lambda document: document.rank)[
            : GenerativeEngineService.PAPER_TOP_K
        ]

    def _validate_strategies(self, strategies: list[str]):
        unknown = [strategy for strategy in strategies if strategy not in STRATEGY_LABELS]

        if unknown:
            raise ValueError(f"Unsupported GEO strategies: {', '.join(unknown)}")
