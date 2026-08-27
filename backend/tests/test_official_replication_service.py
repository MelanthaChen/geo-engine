import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.experiment.official_replication_service import OfficialReplicationService


class OfficialReplicationServiceTests(unittest.TestCase):
    @patch("app.experiment.official_replication_service.OfficialReplicationRunner")
    def test_create_delegates_to_existing_runner_and_records_client_configuration(self, runner_type):
        experiment = SimpleNamespace(id=17)
        runner_type.return_value.create.return_value = experiment
        repository = Mock()
        service = OfficialReplicationService(repository)

        result = service.create(
            stage="stage1",
            subjective=True,
            name="Bridge run",
        )

        self.assertIs(result, experiment)
        runner_type.assert_called_once_with(repository, subjective=True)
        runner_type.return_value.create.assert_called_once_with(stage="stage1", name="Bridge run")
        metadata = repository.add_event.call_args.args[4]
        self.assertEqual(metadata, {"stage": "stage1", "subjective": True})

    def test_detail_reads_existing_artifacts_without_regenerating_them(self):
        now = datetime.now(timezone.utc)
        configured = SimpleNamespace(
            id=1,
            event_type="official_replication_configured",
            metadata_json=json.dumps({"stage": "stage1", "subjective": False}),
            created_at=now,
        )
        started = SimpleNamespace(
            id=2,
            event_type="execution_started",
            metadata_json="{}",
            created_at=now + timedelta(minutes=1),
        )
        experiment = SimpleNamespace(
            id=11,
            created_at=now,
            completed_at=now + timedelta(minutes=31),
            events=[configured, started],
            total_queries=30,
            strategies_json=json.dumps(["original", "citation"]),
            runs=[SimpleNamespace(token_cost=None)],
        )
        repository = Mock()
        repository.get_run.return_value = experiment
        repository.serialize.return_value = {"id": 11, "queryResults": [{"large": "payload"}]}

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "11"
            directory.mkdir()
            (directory / "ReplicationReport.md").write_text("report", encoding="utf-8")
            (directory / "paper_conclusion_verification.json").write_text(
                json.dumps({
                    "trend_similarity": 0.75,
                    "stage_decision": {"decision": "STOP"},
                    "claims": [
                        {"id": "one", "claim": "One", "status": "PASS"},
                        {"id": "two", "claim": "Two", "status": "FAIL"},
                    ],
                }),
                encoding="utf-8",
            )
            detail = OfficialReplicationService(
                repository,
                artifact_root=Path(temporary),
            ).detail(11)

        self.assertEqual(detail["queryResults"], [])
        self.assertEqual(detail["replication"]["trendSimilarity"], 0.75)
        self.assertEqual(detail["replication"]["claimsPassed"], 1)
        self.assertEqual(detail["replication"]["runtimeSeconds"], 30 * 60)
        self.assertIsNone(detail["replication"]["apiCost"])
        self.assertEqual(
            {artifact["name"] for artifact in detail["replication"]["artifacts"]},
            {"ReplicationReport.md", "paper_conclusion_verification.json"},
        )


if __name__ == "__main__":
    unittest.main()
