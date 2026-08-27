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

    provider = Column(
        String,
        nullable=False,
        default="chatgpt",
        server_default="chatgpt",
    )

    llm_model = Column(String, nullable=True)

    dataset_name = Column(String, nullable=True)

    benchmark_queries_json = Column(Text, nullable=True)

    strategies_json = Column(Text, nullable=True)

    metrics_json = Column(Text, nullable=True)

    dataset_id = Column(
        Integer,
        ForeignKey("benchmark_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dataset_version = Column(String, nullable=False, default="1", server_default="1")
    prompt_version_id = Column(
        Integer,
        ForeignKey("experiment_prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generation_params_json = Column(Text, nullable=True)
    run_count = Column(Integer, nullable=False, default=0, server_default="0")

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
    runs = relationship(
        "ExperimentRun",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    statistics = relationship(
        "ExperimentStatistic",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "ExperimentEvent",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    prompt_version = relationship("ExperimentPromptVersion")
    dataset = relationship("BenchmarkDataset")


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

    provider = Column(
        String,
        nullable=False,
        default="chatgpt",
        server_default="chatgpt",
    )

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

    run_id = Column(
        Integer,
        ForeignKey("experiment_runs.id", ondelete="SET NULL"),
        nullable=True,
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
    run = relationship("ExperimentRun", back_populates="strategy_result")


class ExperimentPromptVersion(Base):
    __tablename__ = "experiment_prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Princeton GEO")
    version = Column(String, nullable=False)
    system_template = Column(Text, nullable=False, default="")
    user_template = Column(Text, nullable=False)
    checksum = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    experiment_query_id = Column(
        Integer,
        ForeignKey("experiment_queries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_version_id = Column(
        Integer,
        ForeignKey("experiment_prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    strategy = Column(String, nullable=False, index=True)
    sample_index = Column(Integer, nullable=False, default=0)
    seed_value = Column(Integer, nullable=True)
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued", index=True)
    raw_prompt = Column(Text, nullable=False)
    raw_response = Column(Text, nullable=True)
    generation_params_json = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    token_cost = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="runs")
    prompt_version = relationship("ExperimentPromptVersion")
    strategy_result = relationship(
        "ExperimentStrategyResult",
        back_populates="run",
        uselist=False,
    )
    evaluations = relationship(
        "ExperimentEvaluation",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    metrics = relationship(
        "ExperimentMetric",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class ExperimentEvaluation(Base):
    __tablename__ = "experiment_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluator = Column(String, nullable=False)
    evaluator_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="completed")
    details_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("ExperimentRun", back_populates="evaluations")
    metrics = relationship(
        "ExperimentMetric",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )


class ExperimentMetric(Base):
    __tablename__ = "experiment_metrics"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_id = Column(
        Integer,
        ForeignKey("experiment_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("ExperimentRun", back_populates="metrics")
    evaluation = relationship("ExperimentEvaluation", back_populates="metrics")


class ExperimentStatistic(Base):
    __tablename__ = "experiment_statistics"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy = Column(String, nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)
    sample_count = Column(Integer, nullable=False)
    mean = Column(Float, nullable=True)
    median = Column(Float, nullable=True)
    variance = Column(Float, nullable=True)
    stddev = Column(Float, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    confidence_level = Column(Float, nullable=False, default=0.95)
    confidence_low = Column(Float, nullable=True)
    confidence_high = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="statistics")


class ExperimentEvent(Base):
    __tablename__ = "experiment_events"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="events")
