from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WebsitePage(Base):

    __tablename__ = "website_pages"

    id = Column(Integer, primary_key=True, index=True)

    audit_id = Column(
        Integer,
        ForeignKey("website_audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url = Column(Text, nullable=False)

    page_title = Column(Text, nullable=True)

    meta_description = Column(Text, nullable=True)

    h1 = Column(Text, nullable=True)

    status_code = Column(Integer, nullable=True)

    word_count = Column(Integer, nullable=False, default=0)

    internal_link_count = Column(Integer, nullable=False, default=0)

    external_link_count = Column(Integer, nullable=False, default=0)

    content_sha256 = Column(String(64), nullable=True)

    is_duplicate = Column(Boolean, nullable=False, default=False)

    duplicate_of_url = Column(Text, nullable=True)

    h2_count = Column(Integer, nullable=False, default=0)

    h3_count = Column(Integer, nullable=False, default=0)

    canonical_url = Column(Text, nullable=True)

    schema_types = Column(JSON, nullable=True)

    question_heading_count = Column(Integer, nullable=False, default=0)

    detected_qa_pair_count = Column(Integer, nullable=False, default=0)

    faq_like_heading_count = Column(Integer, nullable=False, default=0)

    faq_page_schema_detected = Column(Boolean, nullable=False, default=False)

    extraction_method = Column(String(20), nullable=True)

    extraction_failure_reason = Column(Text, nullable=True)

    http_word_count = Column(Integer, nullable=True)

    browser_word_count = Column(Integer, nullable=True)

    discovered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    audit = relationship("WebsiteAudit", back_populates="pages")
