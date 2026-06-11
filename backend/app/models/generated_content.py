from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class GeneratedContent(Base):

    __tablename__ = "generated_contents"

    id = Column(Integer, primary_key=True, index=True)

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

    title = Column(String, nullable=False)

    body = Column(Text, nullable=False)

    website_url = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
