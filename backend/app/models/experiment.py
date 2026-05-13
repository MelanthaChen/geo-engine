from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime
)

from sqlalchemy.sql import func

from app.db.database import Base


class Experiment(Base):

    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    status = Column(String, default="running")

    target_platform = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )