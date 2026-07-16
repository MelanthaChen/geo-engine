from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RetrievalTask(Base):

    __tablename__ = "retrieval_tasks"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )

    account_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=True,
        index=True,
    )

    platform = Column(String, nullable=False, index=True)

    category = Column(String, nullable=False, index=True)

    content_type = Column(String, nullable=True)

    status = Column(String, default="queued", index=True)

    result_count = Column(Integer, nullable=True)

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

    completed_at = Column(DateTime(timezone=True), nullable=True)

    property = relationship("Property", back_populates="retrieval_tasks")
    account = relationship("Account")
