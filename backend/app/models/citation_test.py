from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean
)

from sqlalchemy.sql import func

from sqlalchemy.orm import relationship

from app.core.database import Base


class CitationTest(Base):

    __tablename__ = "citation_tests"

    id = Column(Integer, primary_key=True, index=True)

    content_id = Column(
        Integer,
        ForeignKey("contents.id")
    )

    platform = Column(String)

    query = Column(String)

    source_type = Column(String, default="published_content")

    citation_target = Column(Text)

    ai_response = Column(Text)

    mentioned = Column(Boolean)

    evidence_found = Column(Boolean, default=False)

    citation_type = Column(String)

    confidence_score = Column(Integer)

    visibility_score = Column(Integer)

    matched_keywords = Column(Text)

    tested_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    content = relationship("Content")
