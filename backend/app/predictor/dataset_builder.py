"""Collection, validation, statistics, and export for predictor datasets."""

import csv
import io
import json
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.orm import joinedload

from app.models.experiment import Experiment, ExperimentRun
from app.models.training_sample import TrainingSample
from app.predictor.training_sample_repository import TrainingSampleRepository


EXPORT_FIELDS = (
    "experiment_id",
    "experiment_run_id",
    "experiment_query_id",
    "query",
    "strategy",
    "sample_index",
    "original_document",
    "modified_document",
    "prompt",
    "generated_answer",
    "visibility_score",
    "citation_count",
    "subjective_score",
    "pawc",
    "word_score",
    "position_score",
    "llm_provider",
    "llm_model",
    "dataset_name",
    "prompt_version",
    "created_at",
)

REQUIRED_FIELDS = (
    "experiment_id",
    "experiment_run_id",
    "experiment_query_id",
    "query",
    "strategy",
    "original_document",
    "modified_document",
    "prompt",
    "generated_answer",
    "visibility_score",
    "citation_count",
    "pawc",
    "word_score",
    "position_score",
    "llm_provider",
    "llm_model",
)


class DatasetBuilder:
    """Builds clean, traceable supervised records without feature engineering."""

    def __init__(self, repository: TrainingSampleRepository):
        self.repository = repository

    @property
    def db(self):
        return self.repository.db

    def collect_completed_experiment(self, experiment_id: int) -> int:
        """Snapshot every previously uncollected completed run.

        Collection is idempotent because ``experiment_run_id`` is unique. The
        source rows remain authoritative provenance; the snapshot protects
        exported research datasets from later operational changes.
        """
        experiment = (
            self.db.query(Experiment)
            .options(
                joinedload(Experiment.queries),
                joinedload(Experiment.prompt_version),
                joinedload(Experiment.runs).joinedload(ExperimentRun.strategy_result),
                joinedload(Experiment.runs).joinedload(ExperimentRun.metrics),
            )
            .filter(Experiment.id == experiment_id)
            .first()
        )
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")
        if experiment.status != "completed":
            return 0

        completed_runs = [
            run
            for run in experiment.runs
            if run.status == "completed" and run.experiment_query_id is not None
        ]
        existing_ids = self.repository.existing_run_ids([run.id for run in completed_runs])
        samples = [
            self._sample_from_run(experiment, run)
            for run in completed_runs
            if run.id not in existing_ids
        ]
        valid_samples = [sample for sample in samples if not self.missing_fields(sample)]
        self.repository.add_all(valid_samples)
        return len(valid_samples)

    def load_samples(
        self,
        *,
        valid_only: bool = True,
        limit: int | None = None,
    ) -> Sequence[TrainingSample]:
        samples = self.repository.list(limit=limit)
        if not valid_only:
            return samples
        return [sample for sample in samples if not self.missing_fields(sample)]

    def missing_fields(self, sample: TrainingSample) -> list[str]:
        missing = []
        for field in REQUIRED_FIELDS:
            value = getattr(sample, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return missing

    def statistics(self) -> dict[str, Any]:
        samples = list(self.load_samples(valid_only=False))
        invalid = [sample for sample in samples if self.missing_fields(sample)]
        valid = [sample for sample in samples if not self.missing_fields(sample)]
        missing = Counter(
            field
            for sample in samples
            for field in self.missing_fields(sample)
        )
        return {
            "total_samples": len(samples),
            "valid_samples": len(valid),
            "invalid_samples": len(invalid),
            "strategies_covered": len({sample.strategy for sample in valid}),
            "experiments_included": len({sample.experiment_id for sample in valid}),
            "latest_sample_time": self._latest_time(valid),
            "samples_by_strategy": self._counts(valid, "strategy"),
            "samples_by_model": self._counts(valid, "llm_model"),
            "samples_by_provider": self._counts(valid, "llm_provider"),
            "samples_by_experiment": self._counts(valid, "experiment_id"),
            "missing_fields": dict(sorted(missing.items())),
        }

    def export_records(self) -> list[dict[str, Any]]:
        return [self.serialize(sample) for sample in self.load_samples(valid_only=True)]

    def export_csv(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(self.export_records())
        return output.getvalue()

    def export_jsonl(self) -> str:
        return "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in self.export_records()
        )

    @staticmethod
    def serialize(sample: TrainingSample) -> dict[str, Any]:
        record = {}
        for field in EXPORT_FIELDS:
            value = getattr(sample, field)
            record[field] = value.isoformat() if isinstance(value, datetime) else value
        return record

    def _sample_from_run(
        self,
        experiment: Experiment,
        run: ExperimentRun,
    ) -> TrainingSample:
        result = run.strategy_result
        query_row = next(
            (query for query in experiment.queries if query.id == run.experiment_query_id),
            None,
        )
        original_document = next(
            (
                document.plain_text
                for document in (query_row.documents if query_row else [])
                if document.is_selected
            ),
            "",
        )
        metrics = {metric.name: metric.value for metric in run.metrics}
        return TrainingSample(
            experiment_id=experiment.id,
            experiment_run_id=run.id,
            experiment_query_id=run.experiment_query_id,
            query=query_row.query if query_row else "",
            strategy=run.strategy,
            sample_index=run.sample_index,
            original_document=original_document,
            modified_document=result.modified_document_text if result else "",
            prompt=run.raw_prompt,
            generated_answer=run.raw_response or "",
            visibility_score=metrics.get("visibility_score"),
            citation_count=self._integer_metric(metrics.get("citation_count")),
            subjective_score=(
                metrics.get("subjective_impression_calibrated")
                if metrics.get("subjective_impression_calibrated") is not None
                else metrics.get("subjective_impression_raw")
            ),
            pawc=metrics.get("pawc"),
            word_score=metrics.get("word_score"),
            position_score=metrics.get("position_score"),
            llm_provider=run.provider,
            llm_model=run.model,
            dataset_name=experiment.dataset_name,
            prompt_version=(run.prompt_version.version if run.prompt_version else None),
        )

    @staticmethod
    def _integer_metric(value: float | None) -> int | None:
        return int(value) if value is not None else None

    @staticmethod
    def _counts(samples: list[TrainingSample], field: str) -> dict[str, int]:
        counts = Counter(str(getattr(sample, field)) for sample in samples)
        return dict(sorted(counts.items()))

    @staticmethod
    def _latest_time(samples: list[TrainingSample]) -> str | None:
        timestamps = [sample.created_at for sample in samples if sample.created_at]
        return max(timestamps).isoformat() if timestamps else None
