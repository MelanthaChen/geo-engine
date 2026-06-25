from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Property(Base):

    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    domain = Column(String, nullable=False, unique=True, index=True)

    brand_name = Column(String, nullable=True)

    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    contents = relationship("Content", back_populates="property")
    faq_sets = relationship("FaqSet", back_populates="property")
    history_events = relationship(
        "HistoryEvent",
        back_populates="property"
    )
    publish_tasks = relationship("PublishTask", back_populates="property")
    citation_tests = relationship("CitationTest", back_populates="property")
