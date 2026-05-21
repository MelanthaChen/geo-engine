from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime
)

from sqlalchemy.sql import func

from app.core.database import Base


class Campaign(Base):

    __tablename__ = "campaigns"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    target_brand = Column(
        String,
        nullable=False
    )

    target_domain = Column(
        String,
        nullable=True
    )

    target_keywords = Column(
        Text,
        nullable=True
    )

    competitors = Column(
        Text,
        nullable=True
    )

    target_queries = Column(
        Text,
        nullable=True
    )

    campaign_status = Column(
        String,
        default="active"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )