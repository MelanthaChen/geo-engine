import json

from app.ge.ge_service import GenerativeEngineService
from app.ge.geo_rewriter import STRATEGY_LABELS
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


class ExperimentService:
    def __init__(
        self,
        repository: ExperimentRepository,
        ge_service: GenerativeEngineService | None = None,
    ):
        self.repository = repository
        self.ge_service = ge_service or GenerativeEngineService()

    def run_experiment(
        self,
        *,
        property_id: int | None,
        name: str,
        description: str | None,
        llm_model: str,
        dataset_name: str,
        strategies: list[str],
        metrics: list[str],
        number_of_queries: int,
        random_seed: int,
        temperature: float,
        queries: list[str] | None = None,
    ) -> dict:
        self._validate_strategies(strategies)
        experiment = self.create_experiment(
            property_id=property_id,
            name=name,
            description=description,
            llm_model=llm_model,
            dataset_name=dataset_name,
            queries=queries,
            strategies=strategies,
            metrics=metrics,
            number_of_queries=number_of_queries,
            random_seed=random_seed,
            temperature=temperature,
        )
        self.execute_experiment(experiment.id)
        return self.repository.serialize(experiment)

    def create_experiment(
        self,
        *,
        property_id: int | None,
        name: str,
        description: str | None,
        llm_model: str,
        dataset_name: str,
        strategies: list[str],
        metrics: list[str],
        number_of_queries: int,
        random_seed: int,
        temperature: float,
        queries: list[str] | None = None,
    ) -> Experiment:
        self._validate_strategies(strategies)
        benchmark_queries = self._load_queries(number_of_queries, queries)

        return self.repository.create_run(
            property_id=property_id,
            name=name,
            description=description,
            llm_model=llm_model,
            dataset_name=dataset_name,
            benchmark_queries=benchmark_queries,
            strategies=strategies,
            metrics=metrics,
            number_of_queries=len(benchmark_queries),
            random_seed=random_seed,
            temperature=temperature,
        )

    def execute_experiment(self, experiment_id: int) -> Experiment:
        experiment = self.repository.get_run(experiment_id)

        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        strategies = json.loads(experiment.strategies_json or "[]")
        queries = self._load_queries(
            experiment.number_of_queries or 1,
            json.loads(experiment.benchmark_queries_json or "[]"),
        )

        try:
            self.repository.mark_running(experiment)

            for index, query in enumerate(queries):
                self.repository.update_progress(
                    experiment,
                    current_query=query,
                    current_strategy=strategies[0],
                    completed_queries=index,
                )
                result = self.ge_service.run_query(
                    query=query,
                    strategies=strategies,
                    model=experiment.llm_model or "gpt-3.5-turbo",
                    temperature=experiment.temperature or 0.7,
                    random_seed=(experiment.random_seed or 0) + index,
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
                    documents=result["documents"],
                    selected_document_rank=result["selected_document_rank"],
                    strategy_outputs=result["strategy_outputs"],
                )

            self.repository.mark_completed(experiment)
        except Exception as exc:
            self.repository.mark_failed(experiment, str(exc))

        return experiment

    def _load_queries(
        self,
        number_of_queries: int,
        queries: list[str] | None = None,
    ) -> list[str]:
        if queries:
            cleaned_queries = [
                query.strip()
                for query in queries
                if query and query.strip()
            ]

            return cleaned_queries[: max(1, number_of_queries)]

        limit = max(1, min(number_of_queries, len(CUSTOM_BENCHMARK_QUERIES)))
        return CUSTOM_BENCHMARK_QUERIES[:limit]

    def _validate_strategies(self, strategies: list[str]):
        unknown = [strategy for strategy in strategies if strategy not in STRATEGY_LABELS]

        if unknown:
            raise ValueError(f"Unsupported GEO strategies: {', '.join(unknown)}")
