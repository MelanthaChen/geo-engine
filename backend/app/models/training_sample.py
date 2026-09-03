"""Immutable persistence model for GEO Predictor supervised samples."""


from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, event
from sqlalchemy.sql import func

from app.core.database import Base


class TrainingSample(Base):
    """A provenance-linked snapshot derived from a completed GEO run.

    Text and metric values are intentionally snapshotted so an exported
    dataset remains reproducible even if operational experiment records later
    evolve. Foreign keys retain direct provenance to the source objects.
    """

    __tablename__ = "training_samples"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    experiment_run_id = Column(
        Integer,
        ForeignKey("experiment_runs.id", ondelete="SET NULL"),
        nullable=False,
        unique=True,
        index=True,
    )
    experiment_query_id = Column(
        Integer,
        ForeignKey("experiment_queries.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    query = Column(Text, nullable=False)
    strategy = Column(String, nullable=False, index=True)
    sample_index = Column(Integer, nullable=False)
    original_document = Column(Text, nullable=False)
    modified_document = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    generated_answer = Column(Text, nullable=False)
    visibility_score = Column(Float, nullable=True)
    citation_count = Column(Integer, nullable=True)
    subjective_score = Column(Float, nullable=True)
    pawc = Column(Float, nullable=True)
    word_score = Column(Float, nullable=True)
    position_score = Column(Float, nullable=True)
    llm_provider = Column(String, nullable=False, index=True)
    llm_model = Column(String, nullable=False, index=True)
    dataset_name = Column(String, nullable=True, index=True)
    prompt_version = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _prevent_training_sample_mutation(*_args, **_kwargs):
    raise ValueError("TrainingSample records are immutable")


event.listen(TrainingSample, "before_update", _prevent_training_sample_mutation)
event.listen(TrainingSample, "before_delete", _prevent_training_sample_mutation)
