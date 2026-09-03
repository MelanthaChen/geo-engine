"""Persistence boundary for future supervised GEO training samples."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.training_sample import TrainingSample


class TrainingSampleRepository:
    """Owns database access for predictor training samples.

    This module is the foundation for a future GEO prediction system. Keeping
    this boundary separate prevents future dataset construction from leaking
    persistence concerns into trainers or API routes.
    """

    def __init__(self, db: Session):
        self.db = db

    def count(self) -> int:
        return self.db.query(TrainingSample).count()

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[TrainingSample]:
        query = self.db.query(TrainingSample).order_by(TrainingSample.id.asc()).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def existing_run_ids(self, run_ids: list[int]) -> set[int]:
        if not run_ids:
            return set()
        rows = (
            self.db.query(TrainingSample.experiment_run_id)
            .filter(TrainingSample.experiment_run_id.in_(run_ids))
            .all()
        )
        return {row[0] for row in rows}

    def add(self, sample: TrainingSample) -> TrainingSample:
        """Persist a sample once a future dataset builder has validated it."""
        self.db.add(sample)
        self.db.commit()
        self.db.refresh(sample)
        return sample

    def add_all(self, samples: list[TrainingSample]) -> list[TrainingSample]:
        """Insert new immutable samples in one transaction."""
        if not samples:
            return []
        self.db.add_all(samples)
        self.db.commit()
        for sample in samples:
            self.db.refresh(sample)
        return samples
