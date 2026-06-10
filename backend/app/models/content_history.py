from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ContentHistoryEvent(Base):

    __tablename__ = "content_history_events"

    id = Column(Integer, primary_key=True, index=True)

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=True
    )

    event_type = Column(String, nullable=False)

    source_type = Column(String, nullable=True)

    actor = Column(String, default="system")

    status = Column(String, nullable=True)

    summary = Column(Text, nullable=True)

    details = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    content = relationship("Content")
