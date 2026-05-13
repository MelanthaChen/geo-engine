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

from app.db.database import Base


class Content(Base):

    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)

    query_id = Column(
        Integer,
        ForeignKey("queries.id")
    )

    title = Column(String, nullable=False)

    content_type = Column(String)

    body = Column(Text)

    target_persona = Column(String)

    status = Column(String, default="draft")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    query = relationship("Query")