import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ge.geo_rewriter import STRATEGY_LABELS
from app.ge.search_provider import RetrievedDocument
from app.models.experiment import (
    Experiment,
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
        name: str,
        description: str | None,
        llm_model: str,
        dataset_name: str,
        strategies: list[str],
        metrics: list[str],
        number_of_queries: int,
        random_seed: int,
        temperature: float,
    ) -> Experiment:
        experiment = Experiment(
            property_id=property_id,
            name=name,
            description=description,
            status="queued",
            llm_model=llm_model,
            dataset_name=dataset_name,
            strategies_json=json.dumps(strategies),
            metrics_json=json.dumps(metrics),
            number_of_queries=number_of_queries,
            random_seed=random_seed,
            temperature=temperature,
            completed_queries=0,
            total_queries=number_of_queries,
            estimated_remaining_time="Calculating",
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

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
    ):
        experiment.current_query = current_query
        experiment.current_strategy = current_strategy
        self.db.commit()
        self.db.refresh(experiment)

    def store_query_run(
        self,
        experiment: Experiment,
        *,
        query: str,
        documents: list[RetrievedDocument],
        selected_document_rank: int,
        strategy_outputs: list[dict],
    ) -> ExperimentQuery:
        experiment_query = ExperimentQuery(
            experiment_id=experiment.id,
            query=query,
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
                winner = max(
                    query.strategy_results,
                    key=lambda result: result.visibility_score,
                    default=None,
                )

                if winner:
                    winner.is_winner = True

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

        query_results = []

        for query in experiment.queries:
            winner = max(
                query.strategy_results,
                key=lambda result: result.visibility_score,
                default=None,
            )
            query_results.append(
                {
                    "id": str(query.id),
                    "query": query.query,
                    "responses": {
                        result.strategy: result.answer
                        for result in query.strategy_results
                    },
                    "evaluationResult": self._evaluation_summary(winner),
                    "winnerStrategy": winner.strategy if winner else "original",
                }
            )

        return {
            "id": experiment.id,
            "status": experiment.status,
            "currentQuery": experiment.current_query or "",
            "currentStrategy": experiment.current_strategy or "original",
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
            "queryResults": query_results,
            "errorMessage": experiment.error_message,
        }

    def _evaluation_summary(
        self,
        winner: ExperimentStrategyResult | None,
    ) -> str:
        if not winner:
            return "No strategy results were produced."

        label = STRATEGY_LABELS.get(winner.strategy, winner.strategy)
        return (
            f"{label} produced the strongest visibility score for this query "
            f"(visibility {winner.visibility_score:.2f}, "
            f"PAWC {winner.pawc:.2f}, citations {winner.citation_count})."
        )
