from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FaqSet(Base):

    __tablename__ = "faq_sets"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True
    )

    category = Column(String, nullable=False, index=True)

    faq_source = Column(String, nullable=False, index=True)

    content_type = Column(String, nullable=True, index=True)

    website_url = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    property = relationship(
        "Property",
        back_populates="faq_sets"
    )

    faqs = relationship(
        "Faq",
        back_populates="faq_set",
        cascade="all, delete-orphan"
    )
