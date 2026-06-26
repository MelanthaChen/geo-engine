from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WebsiteAudit(Base):

    __tablename__ = "website_audits"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=False,
        index=True,
    )

    base_url = Column(Text, nullable=False)

    status = Column(String, nullable=False, default="completed", index=True)

    brand_summary = Column(Text, nullable=True)

    product_summary = Column(Text, nullable=True)

    target_audience = Column(Text, nullable=True)

    primary_use_cases = Column(Text, nullable=True)

    core_value_proposition = Column(Text, nullable=True)

    overall_geo_score = Column(Integer, nullable=True)

    content_coverage_score = Column(Integer, nullable=True)

    faq_coverage_score = Column(Integer, nullable=True)

    internal_linking_score = Column(Integer, nullable=True)

    website_structure_score = Column(Integer, nullable=True)

    brand_clarity_score = Column(Integer, nullable=True)

    trust_signals_score = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    property = relationship("Property", back_populates="website_audits")

    pages = relationship(
        "WebsitePage",
        back_populates="audit",
        cascade="all, delete-orphan",
    )

    recommendations = relationship(
        "WebsiteAuditRecommendation",
        back_populates="audit",
        cascade="all, delete-orphan",
    )
