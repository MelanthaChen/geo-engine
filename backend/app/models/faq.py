from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Faq(Base):

    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)

    faq_set_id = Column(
        Integer,
        ForeignKey("faq_sets.id"),
        nullable=False,
        index=True
    )

    question = Column(Text, nullable=False)

    rank = Column(Integer, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    faq_set = relationship(
        "FaqSet",
        back_populates="faqs"
    )
