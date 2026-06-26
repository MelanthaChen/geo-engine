from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WebsiteAuditRecommendation(Base):

    __tablename__ = "website_audit_recommendations"

    id = Column(Integer, primary_key=True, index=True)

    audit_id = Column(
        Integer,
        ForeignKey("website_audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category = Column(String, nullable=False, index=True)

    title = Column(Text, nullable=False)

    description = Column(Text, nullable=False)

    priority = Column(String, nullable=False, default="medium")

    evidence_url = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    audit = relationship("WebsiteAudit", back_populates="recommendations")
