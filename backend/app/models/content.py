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


class Content(Base):

    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)

    query_id = Column(
        Integer,
        ForeignKey("queries.id")
    )

    title = Column(String, nullable=False)

    content_type = Column(String)

    generation_mode = Column(
        String,
        nullable=True
    )

    body = Column(Text)

    target_persona = Column(String)

    status = Column(String, default="draft")

    publish_status = Column(
        String,
        default="draft"
    )

    published_url = Column(
        String,
        nullable=True
    )

    publish_provider = Column(
        String,
        nullable=True
    )

    published_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    indexed_status = Column(
        String,
        default="not_indexed"
    )

    citation_count = Column(
        Integer,
        default=0
    )

    visibility_score = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id"),
        nullable=True
    )

    query = relationship("Query")
    campaign = relationship("Campaign")
