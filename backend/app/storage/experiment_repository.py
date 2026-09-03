import json
import logging
import statistics
import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.llm_provider import normalize_llm_provider
from app.ge.geo_rewriter import STRATEGY_LABELS
from app.ge.search_provider import RetrievedDocument
from app.models.experiment import (
    Experiment,
    ExperimentCampaign,
    ExperimentDocument,
    ExperimentQuery,
    ExperimentStrategyResult,
    ExperimentPromptVersion,
    ExperimentRun,
    ExperimentEvaluation,
    ExperimentMetric,
    ExperimentStatistic,
    ExperimentEvent,
)
from app.evaluation.experiment_pipeline import METRIC_UNITS, descriptive_statistics
from app.ge.prompt_builder import GE_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


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
        provider: str | None = None,
        dataset_name: str,
        benchmark_queries: list[Any],
        strategies: list[str],
        metrics: list[str],
        number_of_queries: int,
        random_seed: int,
        temperature: float,
    ) -> Experiment:
        prompt_version = self._get_or_create_prompt_version()
        generation_params = {
            "temperature": temperature,
            "top_p": 1,
            "samples_per_strategy": 5,
            "random_seed": random_seed,
        }
        experiment = Experiment(
            property_id=property_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
            status="queued",
            provider=normalize_llm_provider(provider),
            llm_model=llm_model,
            dataset_name=dataset_name,
            benchmark_queries_json=json.dumps(benchmark_queries),
            strategies_json=json.dumps(strategies),
            metrics_json=json.dumps(metrics),
            dataset_version="1",
            prompt_version_id=prompt_version.id,
            generation_params_json=json.dumps(generation_params),
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
        self.add_event(experiment, "configured", "queued", "Experiment configuration saved")
        return experiment

    def _get_or_create_prompt_version(self) -> ExperimentPromptVersion:
        user_template = "Question: {query}\n\nSearch Results:\n{sources}"
        checksum = hashlib.sha256(
            f"{GE_SYSTEM_PROMPT}\n{user_template}".encode("utf-8")
        ).hexdigest()
        version = (
            self.db.query(ExperimentPromptVersion)
            .filter(ExperimentPromptVersion.checksum == checksum)
            .first()
        )
        if version:
            return version
        version = ExperimentPromptVersion(
            name="Princeton GEO answer prompt",
            version=checksum[:12],
            system_template=GE_SYSTEM_PROMPT,
            user_template=user_template,
            checksum=checksum,
            is_active=True,
        )
        self.db.add(version)
        self.db.flush()
        return version

    def create_campaign(
        self,
        *,
        property_id: int | None,
        name: str,
        description: str | None,
        llm_model: str,
        provider: str | None = None,
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
            provider=normalize_llm_provider(provider),
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
        self.add_event(experiment, "execution_started", "running", "Generation started", commit=False)
        self.db.commit()
        self.db.refresh(experiment)

    def _collect_predictor_training_samples(self, experiment: Experiment) -> None:
        """Collect predictor rows after scientific results are durably complete.

        Dataset collection is deliberately best-effort after the experiment
        transaction commits, so a data-engineering failure cannot change an
        otherwise successful scientific experiment into a failed run.
        """
        try:
            from app.predictor.dataset_builder import DatasetBuilder
            from app.predictor.training_sample_repository import TrainingSampleRepository

            collected = DatasetBuilder(
                TrainingSampleRepository(self.db)
            ).collect_completed_experiment(experiment.id)
            self.add_event(
                experiment,
                "training_samples_collected",
                "completed",
                f"Collected {collected} GEO Predictor training samples",
                metadata={"sample_count": collected},
            )
        except Exception:
            self.db.rollback()
            logger.exception(
                "GEO Predictor sample collection failed for experiment %s",
                experiment.id,
            )

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
            now = datetime.now(timezone.utc)
            run = ExperimentRun(
                experiment_id=experiment.id,
                experiment_query_id=experiment_query.id,
                prompt_version_id=experiment.prompt_version_id,
                strategy=output["strategy"],
                sample_index=output["sample_index"],
                seed_value=seed_value,
                provider=experiment.provider,
                model=experiment.llm_model or "gpt-3.5-turbo",
                status="completed",
                raw_prompt=output["prompt"],
                raw_response=output["answer"],
                generation_params_json=experiment.generation_params_json,
                latency_ms=output.get("latency_ms"),
                started_at=now,
                finished_at=now,
            )
            self.db.add(run)
            self.db.flush()
            evaluation_record = output["evaluation_record"]
            stored_evaluation = ExperimentEvaluation(
                run_id=run.id,
                evaluator=evaluation_record["evaluator"],
                evaluator_version=evaluation_record["evaluator_version"],
                status="completed",
                details_json=json.dumps(evaluation_record["details"]),
            )
            self.db.add(stored_evaluation)
            self.db.flush()
            for name, value in evaluation_record["metrics"].items():
                self.db.add(ExperimentMetric(
                    run_id=run.id,
                    evaluation_id=stored_evaluation.id,
                    name=name,
                    value=float(value) if value is not None else None,
                    unit=METRIC_UNITS.get(name),
                ))
            self.db.add(
                ExperimentStrategyResult(
                    experiment_query_id=experiment_query.id,
                    run_id=run.id,
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

    def ensure_experiment_query(
        self,
        experiment: Experiment,
        *,
        query: str,
        seed_value: int | None,
        documents: list[RetrievedDocument],
        selected_document_rank: int,
    ) -> ExperimentQuery:
        existing = (
            self.db.query(ExperimentQuery)
            .filter(
                ExperimentQuery.experiment_id == experiment.id,
                ExperimentQuery.query == query,
            )
            .first()
        )
        if existing:
            return existing
        row = ExperimentQuery(
            experiment_id=experiment.id,
            query=query,
            seed_value=seed_value,
            selected_document_rank=selected_document_rank,
        )
        self.db.add(row)
        self.db.flush()
        for document in documents:
            self.db.add(ExperimentDocument(
                experiment_query_id=row.id,
                rank=document.rank,
                title=document.title,
                url=document.url,
                plain_text=document.plain_text,
                is_selected=document.rank == selected_document_rank,
            ))
        self.db.commit()
        self.db.refresh(row)
        return row

    def completed_sample_exists(
        self,
        *,
        experiment_id: int,
        experiment_query_id: int,
        strategy: str,
        sample_index: int,
    ) -> bool:
        return self.db.query(ExperimentRun.id).filter(
            ExperimentRun.experiment_id == experiment_id,
            ExperimentRun.experiment_query_id == experiment_query_id,
            ExperimentRun.strategy == strategy,
            ExperimentRun.sample_index == sample_index,
            ExperimentRun.status == "completed",
        ).first() is not None

    def strategy_sample_group(
        self,
        *,
        experiment_id: int,
        experiment_query_id: int,
        strategy: str,
    ) -> list[ExperimentRun]:
        return (
            self.db.query(ExperimentRun)
            .filter(
                ExperimentRun.experiment_id == experiment_id,
                ExperimentRun.experiment_query_id == experiment_query_id,
                ExperimentRun.strategy == strategy,
            )
            .order_by(ExperimentRun.sample_index)
            .all()
        )

    def store_generated_batch(
        self,
        experiment: Experiment,
        experiment_query: ExperimentQuery,
        *,
        query: str,
        strategy: str,
        modified_document_text: str,
        prompt: str,
        answers: list[str],
        seed_value: int | None,
        latency_ms: int | None,
    ) -> list[ExperimentRun]:
        """Durably store the complete official n=5 response before evaluation."""
        if len(answers) != 5:
            raise ValueError(f"Official GEO generation requires five answers, got {len(answers)}")
        existing = self.strategy_sample_group(
            experiment_id=experiment.id,
            experiment_query_id=experiment_query.id,
            strategy=strategy,
        )
        if existing:
            raise RuntimeError("Refusing to overwrite an existing strategy sample group")

        now = datetime.now(timezone.utc)
        runs = []
        for sample_index, answer in enumerate(answers):
            run = ExperimentRun(
                experiment_id=experiment.id,
                experiment_query_id=experiment_query.id,
                prompt_version_id=experiment.prompt_version_id,
                strategy=strategy,
                sample_index=sample_index,
                seed_value=seed_value,
                provider=experiment.provider,
                model=experiment.llm_model or "gpt-3.5-turbo-16k",
                status="generated",
                raw_prompt=prompt,
                raw_response=answer,
                generation_params_json=experiment.generation_params_json,
                latency_ms=latency_ms,
                started_at=now,
            )
            self.db.add(run)
            self.db.flush()
            self.db.add(ExperimentStrategyResult(
                experiment_query_id=experiment_query.id,
                run_id=run.id,
                strategy=strategy,
                sample_index=sample_index,
                modified_document_text=modified_document_text,
                prompt=prompt,
                answer=answer,
                word_count=0,
                position=None,
                pawc=0,
                citation_count=0,
                visibility_score=0,
            ))
            runs.append(run)

        self.db.commit()
        for run in runs:
            self.db.refresh(run)
        return runs

    def complete_generated_sample(self, run: ExperimentRun, *, output: dict) -> ExperimentRun:
        if run.status != "generated" or run.strategy_result is None:
            raise RuntimeError(f"Run {run.id} is not a staged generated sample")
        evaluation = output["evaluation"]
        record = output["evaluation_record"]
        stored_evaluation = ExperimentEvaluation(
            run_id=run.id,
            evaluator=record["evaluator"],
            evaluator_version=record["evaluator_version"],
            status="completed",
            details_json=json.dumps(record["details"]),
        )
        self.db.add(stored_evaluation)
        self.db.flush()
        for name, value in record["metrics"].items():
            self.db.add(ExperimentMetric(
                run_id=run.id,
                evaluation_id=stored_evaluation.id,
                name=name,
                value=float(value) if value is not None else None,
                unit=METRIC_UNITS.get(name, "score"),
            ))
        result = run.strategy_result
        result.word_count = evaluation.word_count
        result.position = evaluation.position
        result.pawc = evaluation.pawc
        result.citation_count = evaluation.citation_count
        result.visibility_score = evaluation.visibility_score
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        run.experiment.run_count = (run.experiment.run_count or 0) + 1
        self.db.commit()
        self.db.refresh(run)
        return run

    def store_completed_sample(
        self,
        experiment: Experiment,
        experiment_query: ExperimentQuery,
        *,
        output: dict,
        seed_value: int | None,
    ) -> ExperimentRun:
        evaluation = output["evaluation"]
        now = datetime.now(timezone.utc)
        run = ExperimentRun(
            experiment_id=experiment.id,
            experiment_query_id=experiment_query.id,
            prompt_version_id=experiment.prompt_version_id,
            strategy=output["strategy"],
            sample_index=output["sample_index"],
            seed_value=seed_value,
            provider=experiment.provider,
            model=experiment.llm_model or "gpt-3.5-turbo",
            status="completed",
            raw_prompt=output["prompt"],
            raw_response=output["answer"],
            generation_params_json=experiment.generation_params_json,
            latency_ms=output.get("latency_ms"),
            started_at=now,
            finished_at=now,
        )
        self.db.add(run)
        self.db.flush()
        record = output["evaluation_record"]
        stored_evaluation = ExperimentEvaluation(
            run_id=run.id,
            evaluator=record["evaluator"],
            evaluator_version=record["evaluator_version"],
            status="completed",
            details_json=json.dumps(record["details"]),
        )
        self.db.add(stored_evaluation)
        self.db.flush()
        for name, value in record["metrics"].items():
            self.db.add(ExperimentMetric(
                run_id=run.id,
                evaluation_id=stored_evaluation.id,
                name=name,
                value=float(value) if value is not None else None,
                unit=METRIC_UNITS.get(name, "score"),
            ))
        self.db.add(ExperimentStrategyResult(
            experiment_query_id=experiment_query.id,
            run_id=run.id,
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
        ))
        experiment.run_count = (experiment.run_count or 0) + 1
        self.db.commit()
        self.db.refresh(run)
        return run

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
        experiment.run_count = len(experiment.runs)

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

        self._store_statistics(experiment)
        self.add_event(experiment, "statistics_completed", "completed", "Metrics aggregated", commit=False)
        self.add_event(experiment, "completed", "completed", "Experiment completed", commit=False)

        self.db.commit()
        self.db.refresh(experiment)
        self._collect_predictor_training_samples(experiment)

    def store_calibrated_subjective_metrics(
        self,
        experiment: Experiment,
        calibrated_by_run_id: dict[int, dict[str, float]],
    ) -> None:
        """Upsert dataset-level calibrated Subjective Impression per completed run."""
        for run in experiment.runs:
            if run.id not in calibrated_by_run_id or not run.evaluations:
                continue
            existing_by_name = {metric.name: metric for metric in run.metrics}
            for name, value in calibrated_by_run_id[run.id].items():
                existing = existing_by_name.get(name)
                if existing:
                    existing.value = value
                else:
                    self.db.add(ExperimentMetric(
                        run_id=run.id,
                        evaluation_id=run.evaluations[0].id,
                        name=name,
                        value=value,
                        unit="ratio",
                        metadata_json=json.dumps({
                            "calibration": "matched to PAWC population mean and variance",
                        }),
                    ))
        self.db.commit()

    def mark_failed(self, experiment: Experiment, error_message: str):
        experiment.status = "failed"
        experiment.error_message = error_message
        experiment.completed_at = datetime.now(timezone.utc)
        self.add_event(experiment, "failed", "failed", error_message, commit=False)
        self.db.commit()
        self.db.refresh(experiment)

    def _store_statistics(self, experiment: Experiment):
        for row in list(experiment.statistics):
            self.db.delete(row)
        grouped = {}
        for run in experiment.runs:
            for metric in run.metrics:
                if metric.value is not None:
                    grouped.setdefault((run.strategy, metric.name), []).append(metric.value)
        for (strategy, metric_name), values in grouped.items():
            summary = descriptive_statistics(values)
            self.db.add(ExperimentStatistic(
                experiment_id=experiment.id,
                strategy=strategy,
                metric_name=metric_name,
                sample_count=summary["sample_count"],
                mean=summary["mean"], median=summary["median"],
                variance=summary["variance"], stddev=summary["stddev"],
                min_value=summary["min"], max_value=summary["max"],
                confidence_level=summary["confidence_level"],
                confidence_low=summary["confidence_low"],
                confidence_high=summary["confidence_high"],
            ))

    def add_event(self, experiment, event_type, status=None, message=None, metadata=None, *, commit=True):
        self.db.add(ExperimentEvent(
            experiment_id=experiment.id,
            event_type=event_type,
            status=status,
            message=message,
            metadata_json=json.dumps(metadata or {}),
        ))
        if commit:
            self.db.commit()

    def list_experiments(self, property_id=None, limit=100):
        query = self.db.query(Experiment)
        if property_id is not None:
            query = query.filter(Experiment.property_id == property_id)
        return query.order_by(Experiment.created_at.desc()).limit(limit).all()

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
            "name": experiment.name,
            "description": experiment.description,
            "propertyId": experiment.property_id,
            "datasetId": experiment.dataset_id,
            "datasetName": experiment.dataset_name,
            "datasetVersion": experiment.dataset_version,
            "model": experiment.llm_model,
            "promptVersion": (
                experiment.prompt_version.version if experiment.prompt_version else None
            ),
            "generationParameters": json.loads(experiment.generation_params_json or "{}"),
            "runCount": experiment.run_count or len(experiment.runs),
            "status": experiment.status,
            "provider": experiment.provider,
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
            "statistics": [
                {
                    "strategy": row.strategy,
                    "metric": row.metric_name,
                    "sampleCount": row.sample_count,
                    "mean": row.mean,
                    "median": row.median,
                    "variance": row.variance,
                    "stddev": row.stddev,
                    "min": row.min_value,
                    "max": row.max_value,
                    "confidenceLevel": row.confidence_level,
                    "confidenceLow": row.confidence_low,
                    "confidenceHigh": row.confidence_high,
                }
                for row in experiment.statistics
            ],
            "timeline": [
                {
                    "type": event.event_type,
                    "status": event.status,
                    "message": event.message,
                    "metadata": json.loads(event.metadata_json or "{}"),
                    "createdAt": event.created_at.isoformat() if event.created_at else None,
                }
                for event in sorted(experiment.events, key=lambda event: event.id)
            ],
            "errorMessage": experiment.error_message,
        }

    def experiment_csv_rows(self, experiment: Experiment) -> list[dict]:
        rows = []
        for run in sorted(experiment.runs, key=lambda item: item.id):
            metrics = {metric.name: metric.value for metric in run.metrics}
            row = {
                "experiment_id": experiment.id,
                "run_id": run.id,
                "query_id": run.experiment_query_id,
                "strategy": run.strategy,
                "sample_index": run.sample_index,
                "seed_value": run.seed_value,
                "provider": run.provider,
                "model": run.model,
                "prompt_version": experiment.prompt_version.version if experiment.prompt_version else None,
                "latency_ms": run.latency_ms,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "total_tokens": run.total_tokens,
                "token_cost": run.token_cost,
                "word_count": metrics.get("word_count"),
                "position": metrics.get("position"),
                "pawc": metrics.get("pawc"),
                "citation_count": metrics.get("citation_count"),
                "visibility_score": metrics.get("visibility_score"),
                "response_length": metrics.get("response_length"),
                "prompt": run.raw_prompt,
                "response": run.raw_response,
            }
            row.update({f"metric_{name}": value for name, value in metrics.items()})
            rows.append(row)
        return rows

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
            "provider": campaign.provider,
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
                            "visibility_improvement": self._relative_improvement(
                                visibility, baseline_visibility,
                            ),
                            "pawc_improvement": self._relative_improvement(
                                pawc, baseline_pawc,
                            ),
                            "citation_count_improvement": self._relative_improvement(
                                citation_count, baseline_citations,
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
                        "visibility_improvement": self._relative_improvement(
                            visibility, baseline_visibility,
                        ),
                        "pawc_improvement": self._relative_improvement(
                            pawc, baseline_pawc,
                        ),
                        "citation_count_improvement": self._relative_improvement(
                            citation_count, baseline_citations,
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
        values = [value for value in values if value is not None]
        if not values:
            return 0.0

        return sum(values) / len(values)

    def _std(self, values: list[float]) -> float:
        values = [value for value in values if value is not None]
        if len(values) < 2:
            return 0.0

        return statistics.stdev(values)

    def _relative_improvement(
        self,
        modified: float,
        baseline: float,
    ) -> float | None:
        if baseline == 0:
            return None

        return ((modified - baseline) / baseline) * 100

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
