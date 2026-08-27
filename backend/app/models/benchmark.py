from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BenchmarkDataset(Base):
    __tablename__ = "benchmark_datasets"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    dataset_type = Column(String, nullable=False, default="question_set", server_default="question_set")
    version = Column(String, nullable=False, default="1", server_default="1")
    checksum = Column(String, nullable=True, index=True)
    is_frozen = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    property = relationship("Property")
    queries = relationship(
        "BenchmarkDatasetQuery",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    benchmarks = relationship("Benchmark", back_populates="dataset")


class BenchmarkDatasetQuery(Base):
    __tablename__ = "benchmark_dataset_queries"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(
        Integer,
        ForeignKey("benchmark_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text = Column(Text, nullable=False)
    rank = Column(Integer, nullable=False, default=1)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dataset = relationship("BenchmarkDataset", back_populates="queries")
    results = relationship("BenchmarkResult", back_populates="dataset_query")


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )
    dataset_id = Column(
        Integer,
        ForeignKey("benchmark_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    providers_json = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    property = relationship("Property")
    dataset = relationship("BenchmarkDataset", back_populates="benchmarks")
    executions = relationship(
        "BenchmarkExecution",
        back_populates="benchmark",
        cascade="all, delete-orphan",
    )


class BenchmarkExecution(Base):
    __tablename__ = "benchmark_executions"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_id = Column(
        Integer,
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )
    dataset_id = Column(
        Integer,
        ForeignKey("benchmark_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider = Column(
        String,
        nullable=False,
        default="chatgpt",
        server_default="chatgpt",
        index=True,
    )
    status = Column(String, nullable=False, default="queued", index=True)
    query_count = Column(Integer, nullable=False, default=0)
    completed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    metrics_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    benchmark = relationship("Benchmark", back_populates="executions")
    property = relationship("Property")
    dataset = relationship("BenchmarkDataset")
    results = relationship(
        "BenchmarkResult",
        back_populates="execution",
        cascade="all, delete-orphan",
    )
    history_events = relationship(
        "HistoryEvent",
        back_populates="benchmark_execution",
    )


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(
        Integer,
        ForeignKey("benchmark_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_query_id = Column(
        Integer,
        ForeignKey("benchmark_dataset_queries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider = Column(
        String,
        nullable=False,
        default="chatgpt",
        server_default="chatgpt",
        index=True,
    )
    query_text = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="queued", index=True)
    latency_ms = Column(Integer, nullable=True)
    mentioned = Column(Integer, nullable=False, default=0)
    rank = Column(Integer, nullable=True)
    recommendation_found = Column(Integer, nullable=False, default=0)
    citation_count = Column(Integer, nullable=False, default=0)
    visibility_score = Column(Integer, nullable=False, default=0)
    response_length = Column(Integer, nullable=False, default=0)
    response_snippet = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    execution = relationship("BenchmarkExecution", back_populates="results")
    dataset_query = relationship("BenchmarkDatasetQuery", back_populates="results")
