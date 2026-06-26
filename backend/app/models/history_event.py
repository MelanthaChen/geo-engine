from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class HistoryEvent(Base):

    __tablename__ = "history_events"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True
    )

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=True,
        index=True
    )

    faq_id = Column(
        Integer,
        ForeignKey("faqs.id"),
        nullable=True,
        index=True
    )

    publishing_job_id = Column(
        Integer,
        ForeignKey("publishing_jobs.id"),
        nullable=True,
        index=True
    )

    citation_test_run_id = Column(
        Integer,
        ForeignKey("citation_test_runs.id"),
        nullable=True,
        index=True
    )

    website_audit_id = Column(
        Integer,
        ForeignKey("website_audits.id"),
        nullable=True,
        index=True,
    )

    event_type = Column(String, nullable=False, index=True)

    summary = Column(Text, nullable=True)

    metadata_json = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    property = relationship("Property", back_populates="history_events")
    content = relationship("Content", back_populates="history_events")
    faq = relationship("Faq")
    publishing_job = relationship(
        "PublishingJob",
        back_populates="history_events",
    )
    citation_test_run = relationship(
        "CitationTestRun",
        back_populates="history_events",
    )
    website_audit = relationship("WebsiteAudit")
