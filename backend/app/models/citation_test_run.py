from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CitationTestRun(Base):

    __tablename__ = "citation_test_runs"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )

    prompt = Column(Text, nullable=False)

    target_brand = Column(String, nullable=True)

    provider = Column(
        String,
        nullable=False,
        default="chatgpt",
        server_default="chatgpt",
    )

    status = Column(String, default="queued", index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    completed_at = Column(DateTime(timezone=True), nullable=True)

    property = relationship("Property", back_populates="citation_test_runs")
    results = relationship(
        "CitationTestResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    history_events = relationship(
        "HistoryEvent",
        back_populates="citation_test_run",
    )
