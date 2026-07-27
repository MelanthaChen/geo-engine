from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Experiment(Base):

    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )

    campaign_id = Column(
        Integer,
        ForeignKey("experiment_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name = Column(String, nullable=False)

    description = Column(Text, nullable=True)

    status = Column(String, default="queued", index=True)

    llm_model = Column(String, nullable=True)

    dataset_name = Column(String, nullable=True)

    benchmark_queries_json = Column(Text, nullable=True)

    strategies_json = Column(Text, nullable=True)

    metrics_json = Column(Text, nullable=True)

    number_of_queries = Column(Integer, nullable=True)

    random_seed = Column(Integer, nullable=True)

    temperature = Column(Float, nullable=True)

    current_query = Column(Text, nullable=True)

    current_strategy = Column(String, nullable=True)

    current_sample = Column(Integer, default=0)

    total_samples = Column(Integer, default=5)

    completed_queries = Column(Integer, default=0)

    total_queries = Column(Integer, default=0)

    estimated_remaining_time = Column(String, nullable=True)

    error_message = Column(Text, nullable=True)

    visibility_score = Column(Float, default=0)

    citation_count = Column(Integer, default=0)

    pawc = Column(Float, default=0)

    target_platform = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    completed_at = Column(DateTime(timezone=True), nullable=True)

    property = relationship("Property")
    campaign = relationship("ExperimentCampaign", back_populates="experiments")
    queries = relationship(
        "ExperimentQuery",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )


class ExperimentCampaign(Base):

    __tablename__ = "experiment_campaigns"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )

    name = Column(String, nullable=False)

    description = Column(Text, nullable=True)

    status = Column(String, default="queued", index=True)

    llm_model = Column(String, nullable=True)

    dataset_name = Column(String, nullable=True)

    benchmark_queries_json = Column(Text, nullable=True)

    strategies_json = Column(Text, nullable=True)

    metrics_json = Column(Text, nullable=True)

    query_count = Column(Integer, nullable=True)

    seed_count = Column(Integer, nullable=True)

    random_seed = Column(Integer, nullable=True)

    temperature = Column(Float, nullable=True)

    current_query = Column(Text, nullable=True)

    current_strategy = Column(String, nullable=True)

    current_seed = Column(Integer, nullable=True)

    queries_completed = Column(Integer, default=0)

    queries_remaining = Column(Integer, default=0)

    success_count = Column(Integer, default=0)

    failure_count = Column(Integer, default=0)

    estimated_remaining_time = Column(String, nullable=True)

    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)

    finished_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    property = relationship("Property")
    experiments = relationship(
        "Experiment",
        back_populates="campaign",
        cascade="save-update, merge",
    )


class ExperimentQuery(Base):

    __tablename__ = "experiment_queries"

    id = Column(Integer, primary_key=True, index=True)

    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    query = Column(Text, nullable=False)

    seed_value = Column(Integer, nullable=True, index=True)

    selected_document_rank = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    experiment = relationship("Experiment", back_populates="queries")
    documents = relationship(
        "ExperimentDocument",
        back_populates="experiment_query",
        cascade="all, delete-orphan",
    )
    strategy_results = relationship(
        "ExperimentStrategyResult",
        back_populates="experiment_query",
        cascade="all, delete-orphan",
    )


class ExperimentDocument(Base):

    __tablename__ = "experiment_documents"

    id = Column(Integer, primary_key=True, index=True)

    experiment_query_id = Column(
        Integer,
        ForeignKey("experiment_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rank = Column(Integer, nullable=False)

    title = Column(Text, nullable=True)

    url = Column(Text, nullable=False)

    plain_text = Column(Text, nullable=False)

    is_selected = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    experiment_query = relationship(
        "ExperimentQuery",
        back_populates="documents",
    )


class ExperimentStrategyResult(Base):

    __tablename__ = "experiment_strategy_results"

    id = Column(Integer, primary_key=True, index=True)

    experiment_query_id = Column(
        Integer,
        ForeignKey("experiment_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    strategy = Column(String, nullable=False, index=True)

    sample_index = Column(Integer, default=0, nullable=False)

    modified_document_text = Column(Text, nullable=False)

    prompt = Column(Text, nullable=False)

    answer = Column(Text, nullable=False)

    word_count = Column(Integer, default=0)

    position = Column(Integer, nullable=True)

    pawc = Column(Float, default=0)

    citation_count = Column(Integer, default=0)

    visibility_score = Column(Float, default=0)

    is_winner = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    experiment_query = relationship(
        "ExperimentQuery",
        back_populates="strategy_results",
    )
