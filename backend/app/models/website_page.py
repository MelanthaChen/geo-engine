from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
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

    discovered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    audit = relationship("WebsiteAudit", back_populates="pages")
