import json
from typing import Any

from app.experiment.experiment_service import (
    PAPER_MODE_SEED_COUNT,
    ExperimentService,
)
from app.models.experiment import ExperimentCampaign
from app.storage.experiment_repository import ExperimentRepository


class ExperimentCampaignService:
    def __init__(
        self,
        repository: ExperimentRepository,
        experiment_service: ExperimentService | None = None,
    ):
        self.repository = repository
        self.experiment_service = experiment_service or ExperimentService(
            repository=repository,
        )

    def create_campaign(
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
        dataset_documents: list[dict[str, Any]] | None = None,
    ) -> ExperimentCampaign:
        self.experiment_service._validate_strategies(strategies)
        strategies = self.experiment_service._paper_mode_strategies(
            dataset_name,
            strategies,
        )
        benchmark_input = self.experiment_service._build_benchmark_input(
            number_of_queries,
            dataset_name,
            queries,
            dataset_documents,
        )
        query_plan, _ = self.experiment_service._load_query_plan(
            number_of_queries,
            benchmark_input,
        )
        seed_count = (
            PAPER_MODE_SEED_COUNT
            if dataset_name == "geo_bench"
            else 1
        )

        return self.repository.create_campaign(
            property_id=property_id,
            name=name,
            description=description,
            llm_model=llm_model,
            dataset_name=dataset_name,
            benchmark_queries=benchmark_input,
            strategies=strategies,
            metrics=metrics,
            query_count=len(query_plan),
            seed_count=seed_count,
            random_seed=random_seed,
            temperature=temperature,
        )

    def execute_campaign(self, campaign_id: int) -> ExperimentCampaign:
        campaign = self.repository.get_campaign(campaign_id)

        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        strategies = json.loads(campaign.strategies_json or "[]")
        metrics = json.loads(campaign.metrics_json or "[]")
        benchmark_input = json.loads(campaign.benchmark_queries_json or "[]")
        queries, documents_by_query = self.experiment_service._load_query_plan(
            campaign.query_count or 1,
            benchmark_input,
        )
        completed_query_labels = {
            self.repository._experiment_query_label(experiment)
            for experiment in campaign.experiments
            if experiment.status == "completed"
        }
        success_count = len(
            [
                experiment
                for experiment in campaign.experiments
                if experiment.status == "completed"
            ]
        )
        failure_count = len(
            [
                experiment
                for experiment in campaign.experiments
                if experiment.status == "failed"
            ]
        )

        try:
            self.repository.mark_campaign_running(campaign)

            for index, query in enumerate(queries):
                if query in completed_query_labels:
                    continue

                self.repository.update_campaign_progress(
                    campaign,
                    current_query=query,
                    current_strategy=strategies[0],
                    current_seed=campaign.random_seed,
                    queries_completed=success_count + failure_count,
                    success_count=success_count,
                    failure_count=failure_count,
                )
                experiment = self._create_child_experiment(
                    campaign=campaign,
                    query=query,
                    documents=documents_by_query.get(query),
                    strategies=strategies,
                    metrics=metrics,
                    random_seed=(campaign.random_seed or 0) + index,
                )
                self.experiment_service.execute_experiment(experiment.id)
                self.repository.db.refresh(experiment)

                if experiment.status == "completed":
                    success_count += 1
                else:
                    failure_count += 1

                self.repository.update_campaign_progress(
                    campaign,
                    current_query=query,
                    current_strategy=experiment.current_strategy or strategies[0],
                    current_seed=experiment.random_seed,
                    queries_completed=success_count + failure_count,
                    success_count=success_count,
                    failure_count=failure_count,
                )

            self.repository.mark_campaign_completed(campaign)
        except Exception as exc:
            self.repository.mark_campaign_failed(campaign, str(exc))

        return campaign

    def _create_child_experiment(
        self,
        *,
        campaign: ExperimentCampaign,
        query: str,
        documents,
        strategies: list[str],
        metrics: list[str],
        random_seed: int,
    ):
        benchmark_entry = self._benchmark_entry_for_query(query, documents)
        query_count = 1
        execution_count = self.experiment_service._execution_count(
            campaign.dataset_name or "",
            query_count,
        )

        return self.repository.create_run(
            property_id=campaign.property_id,
            campaign_id=campaign.id,
            name=f"{campaign.name} · {query[:80]}",
            description=campaign.description,
            llm_model=campaign.llm_model or "gpt-3.5-turbo",
            dataset_name=campaign.dataset_name or "custom",
            benchmark_queries=[benchmark_entry],
            strategies=strategies,
            metrics=metrics,
            number_of_queries=execution_count,
            random_seed=random_seed,
            temperature=campaign.temperature or 0.7,
        )

    def _benchmark_entry_for_query(self, query: str, documents):
        if documents:
            return {
                "query": query,
                "documents": [
                    {
                        "rank": document.rank,
                        "title": document.title,
                        "url": document.url,
                        "content": document.plain_text,
                    }
                    for document in documents
                ],
            }

        return query
