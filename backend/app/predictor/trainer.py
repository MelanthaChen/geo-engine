"""Training interfaces for the future GEO Predictor."""

from dataclasses import dataclass
from typing import Protocol

from app.models.training_sample import TrainingSample


@dataclass(frozen=True)
class TrainingConfiguration:
    embedding_model: str
    target_metric: str
    validation_split: float
    random_seed: int


@dataclass(frozen=True)
class TrainingArtifact:
    artifact_path: str
    model_version: str
    metrics: dict[str, float]


class Trainer(Protocol):
    """Contract for future model trainers.

    This module is the foundation for a future GEO prediction system.
    """

    def train(
        self,
        samples: list[TrainingSample],
        configuration: TrainingConfiguration,
    ) -> TrainingArtifact:
        """Train and persist a versioned model artifact.

        TODO: Implement only after the scientific training protocol is approved.
        """
        ...
