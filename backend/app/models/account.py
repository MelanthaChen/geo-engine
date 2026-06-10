from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime
)

from sqlalchemy.sql import func

from app.core.database import Base


class Account(Base):

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)

    handle = Column(String, unique=True, nullable=False)

    platform = Column(String, nullable=False)

    persona = Column(String, nullable=False)

    lifecycle_stage = Column(String, default="created")

    health_status = Column(String, default="new")

    assigned_topic = Column(String, nullable=True)

    last_action = Column(String, nullable=True)

    notes = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
