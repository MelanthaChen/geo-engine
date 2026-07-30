from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Content(Base):

    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
        index=True
    )

    query_id = Column(
        Integer,
        ForeignKey("queries.id")
    )

    faq_set_id = Column(
        Integer,
        ForeignKey("faq_sets.id"),
        nullable=True,
        index=True
    )

    faq_id = Column(
        Integer,
        ForeignKey("faqs.id"),
        nullable=True,
        index=True
    )

    title = Column(String, nullable=False)

    content_type = Column(String)

    provider = Column(
        String,
        nullable=False,
        default="chatgpt",
        server_default="chatgpt",
    )

    strategy_type = Column(
        String,
        nullable=True
    )

    generation_mode = Column(
        String,
        nullable=True
    )

    target_url = Column(
        String,
        nullable=True
    )

    evidence_json = Column(
        Text,
        nullable=True
    )

    ai_faq = Column(
        Text,
        nullable=True
    )

    platform_faq = Column(
        Text,
        nullable=True
    )

    faq_source = Column(
        String,
        nullable=True
    )

    angle = Column(
        String,
        nullable=True
    )

    perspective = Column(
        String,
        nullable=True
    )

    archetype = Column(
        String,
        nullable=True
    )

    internet_style = Column(
        String,
        nullable=True
    )

    generated_angles = Column(
        Text,
        nullable=True
    )

    body = Column(Text)

    reddit_title = Column(
        String,
        nullable=True
    )

    reddit_body = Column(
        Text,
        nullable=True
    )

    target_persona = Column(String)

    status = Column(String, default="draft")

    publish_status = Column(
        String,
        default="draft"
    )

    published_url = Column(
        String,
        nullable=True
    )

    publish_provider = Column(
        String,
        nullable=True
    )

    publish_platform = Column(
        String,
        nullable=True
    )

    publish_url = Column(
        String,
        nullable=True
    )

    published_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    preview_title = Column(
        String,
        nullable=True
    )

    preview_subreddit = Column(
        String,
        nullable=True
    )

    preview_url = Column(
        String,
        nullable=True
    )

    preview_screenshot = Column(
        String,
        nullable=True
    )

    preview_timestamp = Column(
        DateTime(timezone=True),
        nullable=True
    )

    indexed_status = Column(
        String,
        default="not_indexed"
    )

    citation_count = Column(
        Integer,
        default=0
    )

    visibility_score = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id"),
        nullable=True
    )

    property = relationship("Property", back_populates="contents")
    query = relationship("Query")
    faq_set = relationship("FaqSet")
    faq = relationship("Faq")
    campaign = relationship("Campaign")
    publish_tasks = relationship("PublishTask", back_populates="content")
    publishing_jobs = relationship("PublishingJob", back_populates="content")
    citation_tests = relationship("CitationTest", back_populates="content")
    history_events = relationship("HistoryEvent", back_populates="content")
