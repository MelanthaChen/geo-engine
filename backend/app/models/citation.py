from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Citation(Base):

    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)

    content_id = Column(
        Integer,
        ForeignKey("contents.id")
    )

    platform = Column(String)

    query_used = Column(String)

    cited = Column(Boolean, default=False)

    rank_position = Column(Integer)

    response_snippet = Column(String)

    screenshot_path = Column(String)

    tested_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    content = relationship("Content")