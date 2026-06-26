from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CitationTestResult(Base):

    __tablename__ = "citation_test_results"

    id = Column(Integer, primary_key=True, index=True)

    run_id = Column(
        Integer,
        ForeignKey("citation_test_runs.id"),
        nullable=False,
        index=True,
    )

    model = Column(String, nullable=False)

    status = Column(String, default="queued", index=True)

    mentioned = Column(Boolean, default=False)

    rank = Column(Integer, nullable=True)

    response_snippet = Column(Text, nullable=True)

    raw_response = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)

    tested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run = relationship("CitationTestRun", back_populates="results")
