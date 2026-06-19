from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class GeneratedContent(Base):

    __tablename__ = "generated_contents"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True
    )

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=True,
        index=True
    )

    source_faq_set_id = Column(
        Integer,
        ForeignKey("faq_sets.id"),
        nullable=True,
        index=True
    )

    category = Column(String, nullable=False, index=True)

    faq_source = Column(String, nullable=False, index=True)

    content_type = Column(String, nullable=False, index=True)

    angle = Column(String, nullable=True, index=True)

    perspective = Column(String, nullable=True, index=True)

    archetype = Column(String, nullable=True, index=True)

    internet_style = Column(String, nullable=True, index=True)

    generated_angles = Column(Text, nullable=True)

    title = Column(String, nullable=False)

    body = Column(Text, nullable=False)

    website_url = Column(String, nullable=True)

    generation_timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    property = relationship(
        "Property",
        back_populates="generated_contents"
    )
