import json
import statistics
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.ge.geo_rewriter import STRATEGY_LABELS
from app.ge.search_provider import RetrievedDocument
from app.models.experiment import (
    Experiment,
    ExperimentCampaign,
    ExperimentDocument,
    ExperimentQuery,
    ExperimentStrategyResult,
)


class ExperimentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(
        self,
        *,
        property_id: int | None,
        campaign_id: int | None = None,
        name: str,
        description: str | None,
        llm_model: str,
        dataset_name: str,
        benchmark_queries: list[Any],
        strategies: list[str],
        metrics: list[str],
        number_of_queries: int,
        random_seed: int,
        temperature: float,
    ) -> Experiment:
        experiment = Experiment(
            property_id=property_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
            status="queued",
            llm_model=llm_model,
            dataset_name=dataset_name,
            benchmark_queries_json=json.dumps(benchmark_queries),
            strategies_json=json.dumps(strategies),
            metrics_json=json.dumps(metrics),
            number_of_queries=number_of_queries,
            random_seed=random_seed,
            temperature=temperature,
            current_sample=0,
            total_samples=5,
            completed_queries=0,
            total_queries=number_of_queries,
            estimated_remaining_time="Calculating",
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def create_campaign(
        self,
        *,
        property_id: int | None,
        name: str,
        description: str | None,
        llm_model: str,
        dataset_name: str,
        benchmark_queries: list[Any],
        strategies: list[str],
        metrics: list[str],
        query_count: int,
        seed_count: int,
        random_seed: int,
        temperature: float,
    ) -> ExperimentCampaign:
        campaign = ExperimentCampaign(
            property_id=property_id,
            name=name,
            description=description,
            status="queued",
            llm_model=llm_model,
            dataset_name=dataset_name,
            benchmark_queries_json=json.dumps(benchmark_queries),
            strategies_json=json.dumps(strategies),
            metrics_json=json.dumps(metrics),
            query_count=query_count,
            seed_count=seed_count,
            random_seed=random_seed,
            temperature=temperature,
            current_seed=None,
            queries_completed=0,
            queries_remaining=query_count,
            success_count=0,
            failure_count=0,
            estimated_remaining_time="Calculating",
        )
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def get_campaign(self, campaign_id: int) -> ExperimentCampaign | None:
        return (
            self.db.query(ExperimentCampaign)
            .filter(ExperimentCampaign.id == campaign_id)
            .first()
        )

    def mark_campaign_running(self, campaign: ExperimentCampaign):
        campaign.status = "running"
        campaign.started_at = campaign.started_at or datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(campaign)

    def update_campaign_progress(
        self,
        campaign: ExperimentCampaign,
        *,
        current_query: str,
        current_strategy: str,
        current_seed: int | None,
        queries_completed: int,
        success_count: int,
        failure_count: int,
    ):
        campaign.current_query = current_query
        campaign.current_strategy = current_strategy
        campaign.current_seed = current_seed
        campaign.queries_completed = queries_completed
        campaign.queries_remaining = max((campaign.query_count or 0) - queries_completed, 0)
        campaign.success_count = success_count
        campaign.failure_count = failure_count
        campaign.estimated_remaining_time = (
            f"{campaign.queries_remaining} query batches"
        )
        self.db.commit()
        self.db.refresh(campaign)

    def mark_campaign_completed(self, campaign: ExperimentCampaign):
        campaign.status = "completed"
        campaign.queries_completed = campaign.query_count
        campaign.queries_remaining = 0
        campaign.estimated_remaining_time = "0 min"
        campaign.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(campaign)

    def mark_campaign_failed(
        self,
        campaign: ExperimentCampaign,
        error_message: str,
    ):
        campaign.status = "failed"
        campaign.error_message = error_message
        campaign.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(campaign)

    def mark_running(self, experiment: Experiment):
        experiment.status = "running"
        self.db.commit()
        self.db.refresh(experiment)

    def get_run(self, experiment_id: int) -> Experiment | None:
        return (
            self.db.query(Experiment)
            .filter(Experiment.id == experiment_id)
            .first()
        )

    def update_progress(
        self,
        experiment: Experiment,
        *,
        current_query: str,
        current_strategy: str,
        completed_queries: int,
    ):
        experiment.current_query = current_query
        experiment.current_strategy = current_strategy
        experiment.current_sample = 0
        experiment.completed_queries = completed_queries
        remaining = max((experiment.total_queries or 0) - completed_queries, 0)
        experiment.estimated_remaining_time = f"{remaining} query batches"
        self.db.commit()
        self.db.refresh(experiment)

    def update_current_strategy(
        self,
        experiment: Experiment,
        *,
        current_query: str,
        current_strategy: str,
        current_sample: int = 0,
    ):
        experiment.current_query = current_query
        experiment.current_strategy = current_strategy
        experiment.current_sample = current_sample
        self.db.commit()
        self.db.refresh(experiment)

    def store_query_run(
        self,
        experiment: Experiment,
        *,
        query: str,
        seed_value: int | None = None,
        documents: list[RetrievedDocument],
        selected_document_rank: int,
        strategy_outputs: list[dict],
    ) -> ExperimentQuery:
        experiment_query = ExperimentQuery(
            experiment_id=experiment.id,
            query=query,
            seed_value=seed_value,
            selected_document_rank=selected_document_rank,
        )
        self.db.add(experiment_query)
        self.db.flush()

        for document in documents:
            self.db.add(
                ExperimentDocument(
                    experiment_query_id=experiment_query.id,
                    rank=document.rank,
                    title=document.title,
                    url=document.url,
                    plain_text=document.plain_text,
                    is_selected=document.rank == selected_document_rank,
                )
            )

        for output in strategy_outputs:
            evaluation = output["evaluation"]
            self.db.add(
                ExperimentStrategyResult(
                    experiment_query_id=experiment_query.id,
                    strategy=output["strategy"],
                    sample_index=output["sample_index"],
                    modified_document_text=output["modified_document_text"],
                    prompt=output["prompt"],
                    answer=output["answer"],
                    word_count=evaluation.word_count,
                    position=evaluation.position,
                    pawc=evaluation.pawc,
                    citation_count=evaluation.citation_count,
                    visibility_score=evaluation.visibility_score,
                )
            )

        self.db.commit()
        self.db.refresh(experiment_query)
        return experiment_query

    def mark_completed(self, experiment: Experiment):
        results = [
            result
            for query in experiment.queries
            for result in query.strategy_results
        ]
        experiment.status = "completed"
        experiment.completed_queries = experiment.total_queries
        experiment.estimated_remaining_time = "0 min"
        experiment.completed_at = datetime.now(timezone.utc)

        if results:
            experiment.visibility_score = sum(
                result.visibility_score for result in results
            ) / len(results)
            experiment.citation_count = sum(
                result.citation_count for result in results
            )
            experiment.pawc = sum(result.pawc for result in results) / len(results)

            for query in experiment.queries:
                winner_strategy = self._winner_strategy(query.strategy_results)

                for result in query.strategy_results:
                    result.is_winner = result.strategy == winner_strategy

        self.db.commit()
        self.db.refresh(experiment)

    def mark_failed(self, experiment: Experiment, error_message: str):
        experiment.status = "failed"
        experiment.error_message = error_message
        experiment.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(experiment)

    def serialize(self, experiment: Experiment) -> dict:
        strategy_rows = {}

        for query in experiment.queries:
            for result in query.strategy_results:
                strategy_rows.setdefault(result.strategy, []).append(result)

        strategy_results = [
            {
                "strategy": strategy,
                "label": STRATEGY_LABELS.get(strategy, strategy),
                "visibility": sum(row.visibility_score for row in rows) / len(rows),
                "pawc": sum(row.pawc for row in rows) / len(rows),
                "citationCount": sum(row.citation_count for row in rows),
            }
            for strategy, rows in strategy_rows.items()
        ]
        paper_aggregates = self._paper_aggregates(experiment)

        query_results = []

        for query in experiment.queries:
            winner_strategy = self._winner_strategy(query.strategy_results)
            representative_results = self._representative_results(
                query.strategy_results,
            )
            selected_document = next(
                (
                    document
                    for document in query.documents
                    if document.is_selected
                ),
                None,
            )
            query_results.append(
                {
                    "id": str(query.id),
                    "query": query.query,
                    "seedValue": query.seed_value,
                    "responses": {
                        result.strategy: result.answer
                        for result in representative_results
                    },
                    "evaluationResult": self._evaluation_summary(
                        query.strategy_results,
                        winner_strategy,
                    ),
                    "winnerStrategy": winner_strategy or "original",
                    "evidence": {
                        "topDocuments": [
                            {
                                "rank": document.rank,
                                "title": document.title,
                                "url": document.url,
                                "isSelected": document.is_selected,
                            }
                            for document in sorted(
                                query.documents,
                                key=lambda document: document.rank,
                            )
                        ],
                        "selectedDocumentRank": query.selected_document_rank,
                        "originalDocument": (
                            selected_document.plain_text
                            if selected_document
                            else ""
                        ),
                        "strategyDetails": [
                            {
                                "strategy": result.strategy,
                                "sampleIndex": result.sample_index,
                                "modifiedDocument": result.modified_document_text,
                                "finalPrompt": result.prompt,
                                "generatedAnswer": result.answer,
                                "metrics": {
                                    "wordCount": result.word_count,
                                    "position": result.position,
                                    "pawc": result.pawc,
                                    "citationCount": result.citation_count,
                                    "visibilityScore": result.visibility_score,
                                },
                            }
                            for result in representative_results
                        ],
                    },
                }
            )

        return {
            "id": experiment.id,
            "status": experiment.status,
            "currentQuery": experiment.current_query or "",
            "currentStrategy": experiment.current_strategy or "original",
            "currentSample": experiment.current_sample or 0,
            "totalSamples": experiment.total_samples or 5,
            "completedQueries": experiment.completed_queries or 0,
            "totalQueries": experiment.total_queries or 0,
            "estimatedRemainingTime": (
                experiment.estimated_remaining_time or "Not available"
            ),
            "overall": {
                "visibilityScore": experiment.visibility_score or 0,
                "citationCount": experiment.citation_count or 0,
                "pawc": experiment.pawc or 0,
            },
            "strategyResults": strategy_results,
            "paperAggregates": paper_aggregates,
            "queryResults": query_results,
            "errorMessage": experiment.error_message,
        }

    def serialize_campaign(self, campaign: ExperimentCampaign) -> dict:
        experiments = sorted(
            campaign.experiments,
            key=lambda experiment: experiment.id,
        )
        aggregates = self._campaign_aggregates(campaign)

        return {
            "id": campaign.id,
            "status": campaign.status,
            "name": campaign.name,
            "description": campaign.description,
            "datasetName": campaign.dataset_name,
            "model": campaign.llm_model,
            "queryCount": campaign.query_count or 0,
            "seedCount": campaign.seed_count or 0,
            "strategies": json.loads(campaign.strategies_json or "[]"),
            "metrics": json.loads(campaign.metrics_json or "[]"),
            "currentQuery": campaign.current_query or "",
            "currentStrategy": campaign.current_strategy or "original",
            "currentSeed": campaign.current_seed,
            "queriesCompleted": campaign.queries_completed or 0,
            "queriesRemaining": campaign.queries_remaining or 0,
            "successCount": campaign.success_count or 0,
            "failureCount": campaign.failure_count or 0,
            "estimatedRemainingTime": (
                campaign.estimated_remaining_time or "Not available"
            ),
            "startedAt": campaign.started_at.isoformat() if campaign.started_at else None,
            "finishedAt": (
                campaign.finished_at.isoformat() if campaign.finished_at else None
            ),
            "createdAt": campaign.created_at.isoformat() if campaign.created_at else None,
            "errorMessage": campaign.error_message,
            "paperAggregates": aggregates,
            "strategyResults": self._campaign_strategy_results(aggregates),
            "experiments": [
                {
                    "id": experiment.id,
                    "status": experiment.status,
                    "query": self._experiment_query_label(experiment),
                    "errorMessage": experiment.error_message,
                    "paperAggregates": self._paper_aggregates(experiment),
                }
                for experiment in experiments
            ],
            "queryResults": [
                query_result
                for experiment in experiments
                for query_result in self.serialize(experiment)["queryResults"]
            ],
        }

    def campaign_json_export(self, campaign: ExperimentCampaign) -> dict:
        payload = self.serialize_campaign(campaign)
        payload["experiments"] = [
            self.serialize(experiment)
            for experiment in sorted(
                campaign.experiments,
                key=lambda row: row.id,
            )
        ]
        return payload

    def campaign_csv_rows(self, campaign: ExperimentCampaign) -> list[dict]:
        rows = []

        for experiment in sorted(campaign.experiments, key=lambda row: row.id):
            for query in sorted(experiment.queries, key=lambda row: row.id):
                for result in sorted(
                    query.strategy_results,
                    key=lambda row: (row.strategy, row.sample_index),
                ):
                    rows.append(
                        {
                            "campaign_id": campaign.id,
                            "experiment_id": experiment.id,
                            "experiment_status": experiment.status,
                            "query_id": query.id,
                            "query": query.query,
                            "seed_value": query.seed_value,
                            "selected_document_rank": query.selected_document_rank,
                            "strategy": result.strategy,
                            "sample_index": result.sample_index,
                            "word_count": result.word_count,
                            "position": result.position,
                            "pawc": result.pawc,
                            "citation_count": result.citation_count,
                            "visibility_score": result.visibility_score,
                            "prompt": result.prompt,
                            "answer": result.answer,
                            "modified_document_text": result.modified_document_text,
                        }
                    )

        return rows

    def _campaign_aggregates(self, campaign: ExperimentCampaign) -> list[dict]:
        grouped_scores: dict[str, list[dict[str, float]]] = {}

        for experiment in campaign.experiments:
            for query in experiment.queries:
                per_strategy = {}

                for result in query.strategy_results:
                    per_strategy.setdefault(result.strategy, []).append(result)

                if not per_strategy:
                    continue

                baseline_rows = per_strategy.get("original", [])
                baseline_visibility = self._mean(
                    [row.visibility_score or 0 for row in baseline_rows],
                )
                baseline_pawc = self._mean([row.pawc or 0 for row in baseline_rows])
                baseline_citations = self._mean(
                    [row.citation_count or 0 for row in baseline_rows],
                )

                for strategy, rows in per_strategy.items():
                    visibility = self._mean(
                        [row.visibility_score or 0 for row in rows],
                    )
                    pawc = self._mean([row.pawc or 0 for row in rows])
                    citation_count = self._mean(
                        [row.citation_count or 0 for row in rows],
                    )
                    grouped_scores.setdefault(strategy, []).append(
                        {
                            "visibility": visibility,
                            "pawc": pawc,
                            "citation_count": citation_count,
                            "baseline_visibility": baseline_visibility,
                            "baseline_pawc": baseline_pawc,
                            "baseline_citation_count": baseline_citations,
                            "visibility_improvement": visibility - baseline_visibility,
                            "pawc_improvement": pawc - baseline_pawc,
                            "citation_count_improvement": (
                                citation_count - baseline_citations
                            ),
                        }
                    )

        return self._aggregate_score_rows(grouped_scores)

    def _campaign_strategy_results(self, aggregates: list[dict]) -> list[dict]:
        return [
            {
                "strategy": row["strategy"],
                "label": row["label"],
                "visibility": row["visibilityMean"],
                "pawc": row["pawcMean"],
                "citationCount": round(row["citationCountMean"] * row["runs"]),
            }
            for row in aggregates
        ]

    def _experiment_query_label(self, experiment: Experiment) -> str:
        query = next(iter(experiment.queries), None)

        if query:
            return query.query

        try:
            benchmark_queries = json.loads(experiment.benchmark_queries_json or "[]")
        except Exception:
            benchmark_queries = []

        if benchmark_queries and isinstance(benchmark_queries[0], dict):
            return str(benchmark_queries[0].get("query") or "")

        if benchmark_queries:
            return str(benchmark_queries[0])

        return ""

    def _paper_aggregates(self, experiment: Experiment) -> list[dict]:
        grouped_scores: dict[str, list[dict[str, float]]] = {}

        for query in experiment.queries:
            per_strategy = {}

            for result in query.strategy_results:
                per_strategy.setdefault(result.strategy, []).append(result)

            if not per_strategy:
                continue

            baseline_rows = per_strategy.get("original", [])
            baseline_visibility = self._mean(
                [row.visibility_score or 0 for row in baseline_rows],
            )
            baseline_pawc = self._mean(
                [row.pawc or 0 for row in baseline_rows],
            )
            baseline_citations = self._mean(
                [row.citation_count or 0 for row in baseline_rows],
            )

            for strategy, rows in per_strategy.items():
                visibility = self._mean(
                    [row.visibility_score or 0 for row in rows],
                )
                pawc = self._mean([row.pawc or 0 for row in rows])
                citation_count = self._mean(
                    [row.citation_count or 0 for row in rows],
                )
                grouped_scores.setdefault(strategy, []).append(
                    {
                        "visibility": visibility,
                        "pawc": pawc,
                        "citation_count": citation_count,
                        "baseline_visibility": baseline_visibility,
                        "baseline_pawc": baseline_pawc,
                        "baseline_citation_count": baseline_citations,
                        "visibility_improvement": visibility - baseline_visibility,
                        "pawc_improvement": pawc - baseline_pawc,
                        "citation_count_improvement": (
                            citation_count - baseline_citations
                        ),
                    }
                )

        return self._aggregate_score_rows(grouped_scores)

    def _aggregate_score_rows(
        self,
        grouped_scores: dict[str, list[dict[str, float]]],
    ) -> list[dict]:
        aggregates = []

        for strategy, rows in grouped_scores.items():
            aggregates.append(
                {
                    "strategy": strategy,
                    "label": STRATEGY_LABELS.get(strategy, strategy),
                    "runs": len(rows),
                    "visibilityMean": self._mean(
                        [row["visibility"] for row in rows],
                    ),
                    "visibilityStd": self._std(
                        [row["visibility"] for row in rows],
                    ),
                    "pawcMean": self._mean([row["pawc"] for row in rows]),
                    "pawcStd": self._std([row["pawc"] for row in rows]),
                    "citationCountMean": self._mean(
                        [row["citation_count"] for row in rows],
                    ),
                    "citationCountStd": self._std(
                        [row["citation_count"] for row in rows],
                    ),
                    "baselineVisibilityMean": self._mean(
                        [row["baseline_visibility"] for row in rows],
                    ),
                    "baselinePawcMean": self._mean(
                        [row["baseline_pawc"] for row in rows],
                    ),
                    "baselineCitationCountMean": self._mean(
                        [row["baseline_citation_count"] for row in rows],
                    ),
                    "visibilityImprovementMean": self._mean(
                        [row["visibility_improvement"] for row in rows],
                    ),
                    "visibilityImprovementStd": self._std(
                        [row["visibility_improvement"] for row in rows],
                    ),
                    "pawcImprovementMean": self._mean(
                        [row["pawc_improvement"] for row in rows],
                    ),
                    "pawcImprovementStd": self._std(
                        [row["pawc_improvement"] for row in rows],
                    ),
                    "citationCountImprovementMean": self._mean(
                        [row["citation_count_improvement"] for row in rows],
                    ),
                    "citationCountImprovementStd": self._std(
                        [row["citation_count_improvement"] for row in rows],
                    ),
                }
            )

        return sorted(
            aggregates,
            key=lambda row: row["visibilityImprovementMean"],
            reverse=True,
        )

    def _winner_strategy(self, results):
        if not results:
            return None

        grouped = {}

        for result in results:
            grouped.setdefault(result.strategy, []).append(result.visibility_score)

        return max(
            grouped.items(),
            key=lambda item: sum(item[1]) / len(item[1]),
        )[0]

    def _representative_results(self, results):
        representative = {}

        for result in sorted(results, key=lambda item: item.sample_index):
            representative.setdefault(result.strategy, result)

        return list(representative.values())

    def _mean(self, values: list[float]) -> float:
        if not values:
            return 0.0

        return sum(values) / len(values)

    def _std(self, values: list[float]) -> float:
        if len(values) < 2:
            return 0.0

        return statistics.stdev(values)

    def _evaluation_summary(
        self,
        results,
        winner_strategy: str | None,
    ) -> str:
        if not winner_strategy:
            return "No strategy results were produced."

        winner_rows = [
            result
            for result in results
            if result.strategy == winner_strategy
        ]
        avg_visibility = sum(
            result.visibility_score for result in winner_rows
        ) / len(winner_rows)
        avg_pawc = sum(result.pawc for result in winner_rows) / len(winner_rows)
        citation_count = sum(result.citation_count for result in winner_rows)
        label = STRATEGY_LABELS.get(winner_strategy, winner_strategy)
        return (
            f"{label} produced the strongest mean visibility score across "
            f"the five sampled answers for this query "
            f"(visibility {avg_visibility:.4f}, "
            f"PAWC {avg_pawc:.4f}, citations {citation_count})."
        )
