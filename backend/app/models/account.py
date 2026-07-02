from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Account(Base):

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)

    handle = Column(String, unique=True, nullable=False)

    account_key = Column(String, unique=True, nullable=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )

    agent_name = Column(String, nullable=True)

    state_identifier = Column(String, nullable=True)

    session_path = Column(String, nullable=True)

    session_status = Column(String, nullable=True)

    last_login = Column(DateTime(timezone=True), nullable=True)

    last_session_refresh = Column(DateTime(timezone=True), nullable=True)

    last_session_validation = Column(DateTime(timezone=True), nullable=True)

    browser_profile_name = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)

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

    property = relationship("Property", back_populates="accounts")
