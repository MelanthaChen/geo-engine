import unittest
import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.experiment import (
    Experiment,
    ExperimentDocument,
    ExperimentEvaluation,
    ExperimentMetric,
    ExperimentPromptVersion,
    ExperimentQuery,
    ExperimentRun,
    ExperimentStrategyResult,
)
from app.predictor.dataset_builder import DatasetBuilder
from app.predictor.predictor_service import PredictorService
from app.predictor.schemas import PredictorPredictRequest, PredictorTrainRequest
from app.predictor.training_sample_repository import TrainingSampleRepository
from app.storage.experiment_repository import ExperimentRepository


class FakeTrainingSampleRepository:
    def __init__(self, sample_count: int = 0):
        self.sample_count = sample_count

    def count(self) -> int:
        return self.sample_count

    def list(self, **_kwargs):
        return []


class PredictorFoundationTests(unittest.TestCase):
    def test_status_never_claims_a_model_is_ready(self):
        service = PredictorService(FakeTrainingSampleRepository())

        status = service.status()

        self.assertEqual(status.status, "foundation_ready")
        self.assertFalse(status.model_ready)

    def test_empty_dataset_is_reported_explicitly(self):
        service = PredictorService(FakeTrainingSampleRepository())

        dataset = service.dataset_overview()

        self.assertEqual(dataset.status, "empty")
        self.assertEqual(dataset.total_samples, 0)

    def test_train_and_predict_are_structured_placeholders(self):
        service = PredictorService(FakeTrainingSampleRepository())
        configuration = PredictorTrainRequest()

        train_result = service.train(configuration)
        prediction = service.predict(
            PredictorPredictRequest(
                query="What improves GEO visibility?",
                strategy="citation",
                original_document="Original source text.",
                modified_document="Modified source text with citations.",
            )
        )

        self.assertEqual(train_result.status, "not_implemented")
        self.assertEqual(train_result.accepted_configuration, configuration)
        self.assertEqual(prediction.status, "not_implemented")
        self.assertIsNone(prediction.prediction)


class PredictorDatasetPipelineTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_completed_experiment_is_collected_once_and_exports_cleanly(self):
        experiment = self._completed_experiment_fixture()
        repository = ExperimentRepository(self.db)

        repository.mark_completed(experiment)
        repository.mark_completed(experiment)

        builder = DatasetBuilder(TrainingSampleRepository(self.db))
        summary = builder.statistics()
        records = builder.export_records()

        self.assertEqual(summary["total_samples"], 1)
        self.assertEqual(summary["valid_samples"], 1)
        self.assertEqual(summary["invalid_samples"], 0)
        self.assertEqual(summary["samples_by_strategy"], {"citation": 1})
        self.assertEqual(summary["samples_by_model"], {"test-model": 1})
        self.assertEqual(summary["samples_by_provider"], {"chatgpt": 1})
        self.assertEqual(summary["samples_by_experiment"], {str(experiment.id): 1})
        self.assertEqual(records[0]["experiment_run_id"], experiment.runs[0].id)
        self.assertEqual(records[0]["query"], "What is GEO?")
        self.assertEqual(records[0]["generated_answer"], "Grounded answer [1].")
        self.assertIn("experiment_run_id", builder.export_csv().splitlines()[0])
        self.assertEqual(json.loads(builder.export_jsonl())["pawc"], 0.7)

    def _completed_experiment_fixture(self):
        prompt_version = ExperimentPromptVersion(
            name="test prompt",
            version="v1",
            system_template="",
            user_template="Question: {query}",
            checksum="predictor-test-v1",
            is_active=True,
        )
        experiment = Experiment(
            name="Dataset collection fixture",
            status="running",
            provider="chatgpt",
            llm_model="test-model",
            dataset_name="geo_bench",
            dataset_version="1",
            prompt_version=prompt_version,
            benchmark_queries_json="[]",
            strategies_json='["citation"]',
            metrics_json='["pawc"]',
            total_queries=1,
            completed_queries=1,
            run_count=1,
        )
        query = ExperimentQuery(
            experiment=experiment,
            query="What is GEO?",
            seed_value=42,
            selected_document_rank=1,
        )
        query.documents.append(ExperimentDocument(
            rank=1,
            title="Selected source",
            url="https://example.com/source",
            plain_text="Original selected document.",
            is_selected=True,
        ))
        run = ExperimentRun(
            experiment=experiment,
            experiment_query_id=None,
            prompt_version=prompt_version,
            strategy="citation",
            sample_index=0,
            seed_value=42,
            provider="chatgpt",
            model="test-model",
            status="completed",
            raw_prompt="Official prompt",
            raw_response="Grounded answer [1].",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
        self.db.add_all([experiment, query, run])
        self.db.flush()
        run.experiment_query_id = query.id
        result = ExperimentStrategyResult(
            experiment_query=query,
            run=run,
            strategy="citation",
            sample_index=0,
            modified_document_text="Modified selected document.",
            prompt="Official prompt",
            answer="Grounded answer [1].",
            word_count=3,
            position=1,
            pawc=0.7,
            citation_count=1,
            visibility_score=0.8,
        )
        evaluation = ExperimentEvaluation(
            run=run,
            evaluator="test",
            evaluator_version="1",
            status="completed",
        )
        self.db.add_all([result, evaluation])
        self.db.flush()
        for name, value in {
            "visibility_score": 0.8,
            "citation_count": 1,
            "pawc": 0.7,
            "word_score": 0.6,
            "position_score": 0.9,
            "subjective_impression_raw": 0.75,
        }.items():
            self.db.add(ExperimentMetric(
                run=run,
                evaluation=evaluation,
                name=name,
                value=value,
                unit="ratio",
            ))
        self.db.commit()
        self.db.refresh(experiment)
        return experiment


if __name__ == "__main__":
    unittest.main()
