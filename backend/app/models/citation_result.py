from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CitationResult(Base):

    __tablename__ = "citation_results"

    id = Column(Integer, primary_key=True, index=True)

    citation_test_id = Column(
        Integer,
        ForeignKey("citation_tests.id"),
        nullable=False,
        index=True
    )

    model = Column(String, nullable=False)

    mentioned = Column(Boolean, default=False)

    rank = Column(Integer, nullable=True)

    response = Column(Text, nullable=True)

    tested_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    citation_test = relationship(
        "CitationTest",
        back_populates="results"
    )
