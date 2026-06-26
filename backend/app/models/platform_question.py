from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PlatformQuestion(Base):

    __tablename__ = "platform_questions"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True,
    )

    platform = Column(String, nullable=False, index=True)

    title = Column(Text, nullable=False)

    body = Column(Text, nullable=True)

    url = Column(String, nullable=True)

    author = Column(String, nullable=True)

    score = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=True)

    discovered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    content_hash = Column(String, nullable=False, index=True)

    property = relationship(
        "Property",
        back_populates="platform_questions",
    )
