from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PublishTask(Base):

    __tablename__ = "publish_tasks"

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
        nullable=False
    )

    account_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=False
    )

    status = Column(String, default="pending")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    property = relationship("Property", back_populates="publish_tasks")
    content = relationship("Content", back_populates="publish_tasks")
    account = relationship("Account")
