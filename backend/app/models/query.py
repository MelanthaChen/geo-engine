from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.db.database import Base


class Query(Base):

    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True)

    query_text = Column(String, nullable=False)

    category = Column(String)

    intent = Column(String)

    cluster_name = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )