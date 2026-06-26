from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PublishingJob(Base):

    __tablename__ = "publishing_jobs"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=False,
        index=True,
    )

    account_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )

    platform = Column(String, nullable=False)

    status = Column(String, default="queued", index=True)

    logs = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    property = relationship("Property", back_populates="publishing_jobs")
    content = relationship("Content", back_populates="publishing_jobs")
    account = relationship("Account")
    history_events = relationship(
        "HistoryEvent",
        back_populates="publishing_job",
    )
