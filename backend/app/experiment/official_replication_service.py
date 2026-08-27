import json
from datetime import datetime, timezone
from pathlib import Path

from app.experiment.official_replication_runner import OfficialReplicationRunner
from app.experiment.trend_validation import STAGES
from app.storage.experiment_repository import ExperimentRepository


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "replication_artifacts"


class OfficialReplicationService:
    """Shared orchestration for the CLI and web clients of the official runner."""

    def __init__(
        self,
        repository: ExperimentRepository,
        *,
        artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    ):
        self.repository = repository
        self.artifact_root = Path(artifact_root)

    def create(self, *, stage: str, subjective: bool, name: str | None = None):
        if stage not in STAGES:
            raise ValueError(f"Unknown replication stage: {stage}")
        runner = OfficialReplicationRunner(self.repository, subjective=subjective)
        experiment = runner.create(
            stage=stage,
            name=(name or "Official Princeton GEO Replication").strip()
            or "Official Princeton GEO Replication",
        )
        self.repository.add_event(
            experiment,
            "official_replication_configured",
            "queued",
            "Official Princeton GEO replication configured",
            {"stage": stage, "subjective": subjective},
        )
        return experiment

    def execute(self, experiment_id: int, *, subjective: bool | None = None) -> Path:
        experiment = self.repository.get_run(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        configured = self._configuration(experiment)
        enabled = configured.get("subjective", False) if subjective is None else subjective
        runner = OfficialReplicationRunner(self.repository, subjective=bool(enabled))
        try:
            runner.execute(experiment_id)
        except Exception as exc:
            current = self.repository.get_run(experiment_id)
            if current and current.status != "failed":
                self.repository.mark_failed(current, str(exc))
            raise
        return runner.export(experiment_id, self.artifact_dir(experiment_id))

    def detail(self, experiment_id: int) -> dict:
        experiment = self.repository.get_run(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        payload = self.repository.serialize(experiment)
        # Replication pages consume aggregate state and generated artifacts. Avoid
        # transferring every full prompt/answer through the polling endpoint.
        payload["queryResults"] = []
        payload.update(
            {
                "createdAt": self._iso(experiment.created_at),
                "startedAt": self._started_at(experiment),
                "finishedAt": self._iso(experiment.completed_at),
                "replication": self._replication_payload(experiment),
            }
        )
        return payload

    def list(self) -> list[dict]:
        return [
            self.detail(experiment.id)
            for experiment in self.repository.list_experiments()
            if self._is_official(experiment)
        ]

    def artifact_dir(self, experiment_id: int) -> Path:
        return self.artifact_root / str(experiment_id)

    def artifact_path(self, experiment_id: int, relative_path: str) -> Path:
        root = self.artifact_dir(experiment_id).resolve()
        candidate = (root / relative_path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            raise FileNotFoundError(relative_path)
        return candidate

    def _replication_payload(self, experiment) -> dict:
        directory = self.artifact_dir(experiment.id)
        verification = self._read_json(directory / "paper_conclusion_verification.json")
        config = self._configuration(experiment)
        artifacts = []
        if directory.is_dir():
            for path in sorted(directory.rglob("*")):
                if path.is_file() and not path.name.startswith(".") and path.name != "generate_figures.py":
                    artifacts.append(
                        {
                            "name": path.name,
                            "path": path.relative_to(directory).as_posix(),
                            "kind": self._artifact_kind(path),
                        }
                    )
        claims = verification.get("claims", []) if verification else []
        passed = sum(claim.get("status") == "PASS" for claim in claims)
        testable = sum(claim.get("status") in {"PASS", "FAIL"} for claim in claims)
        started = self._started_datetime(experiment)
        finished = experiment.completed_at
        runtime_seconds = None
        if started:
            end = finished or datetime.now(timezone.utc)
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            runtime_seconds = max(0, int((end - started).total_seconds()))
        cost = sum(
            run.token_cost for run in experiment.runs if run.token_cost is not None
        )
        has_cost = any(run.token_cost is not None for run in experiment.runs)
        return {
            "stage": config.get("stage") or self._stage(experiment.total_queries),
            "subjectiveEnabled": bool(config.get("subjective", False)),
            "strategyCount": len(json.loads(experiment.strategies_json or "[]")),
            "runtimeSeconds": runtime_seconds,
            "apiCost": cost if has_cost else None,
            "trendSimilarity": verification.get("trend_similarity") if verification else None,
            "claimsPassed": passed if verification else None,
            "claimsTested": testable if verification else None,
            "stageDecision": (verification.get("stage_decision") or {}).get("decision") if verification else None,
            "claims": claims,
            "artifacts": artifacts,
        }

    @staticmethod
    def _configuration(experiment) -> dict:
        for event in experiment.events:
            if event.event_type == "official_replication_configured":
                return json.loads(event.metadata_json or "{}")
        return {}

    @classmethod
    def _is_official(cls, experiment) -> bool:
        return (
            experiment.dataset_name == "geo_bench"
            and (
                bool(cls._configuration(experiment))
                or (experiment.description or "").startswith("Official GEO-bench staged replication:")
            )
        )

    @staticmethod
    def _stage(query_count: int | None) -> str:
        return next(
            (stage for stage, config in STAGES.items() if config["queries"] == query_count),
            "full",
        )

    @staticmethod
    def _artifact_kind(path: Path) -> str:
        if path.suffix.lower() in {".png", ".svg"}:
            return "figure"
        if path.suffix.lower() == ".md":
            return "report"
        return path.suffix.lower().lstrip(".") or "file"

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _started_datetime(experiment):
        events = sorted(experiment.events, key=lambda event: event.id)
        event = next((row for row in events if row.event_type == "execution_started"), None)
        return event.created_at if event else None

    @classmethod
    def _started_at(cls, experiment) -> str | None:
        return cls._iso(cls._started_datetime(experiment))

    @staticmethod
    def _iso(value) -> str | None:
        return value.isoformat() if value else None
