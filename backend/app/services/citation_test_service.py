from openai import OpenAI
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings

from app.models.content import Content
from app.models.citation_test import CitationTest
from app.models.citation_result import CitationResult
from app.repositories.history_repository import (
    create_history_event
)
from app.utils.title_extractor import (
    extract_article_title
)


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def run_citation_test(
    db: Session,
    content_id: int,
    platform: str = "openai",
    source_type: str = "published_content",
    property_id: int | None = None,
):

    query = db.query(Content).filter(Content.id == content_id)

    if property_id is not None:
        query = query.filter(Content.property_id == property_id)

    content = query.first()

    if not content:
        return None

    article_title = extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )

    test_query = (
        f"What do people say about {article_title}? "
        "Mention useful sources if you know them."
    )

    citation_target = content.published_url or article_title

    create_history_event(
        db=db,
        event_type="citation_test_started",
        property_id=content.property_id,
        content_id=content.id,
        summary=f"Citation test started for {article_title}",
        details=test_query,
    )

    if source_type == "personal_comment":
        context_message = f"""
Personal comment to evaluate as a possible citation source:

{content.body[:1200]}

When answering, only cite or attribute this comment if it is relevant.
"""
    else:
        context_message = f"""
Published content to evaluate as a possible citation source:

Title: {article_title}
URL: {content.published_url or "not published yet"}
Excerpt:
{content.body[:1200]}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": """
You are an AI assistant helping users answer questions.

Give natural recommendation-style answers.
When citing source material, name whether it is a public source,
published content, or a personal comment.
"""
            },
            {
                "role": "user",
                "content": context_message
            },
            {
                "role": "user",
                "content": test_query
            }
        ],
        temperature=0.7
    )

    ai_response = response.choices[0].message.content

    matched_keywords = []

    title_words = article_title.lower().split()

    for word in title_words:

        if word in ai_response.lower():

            matched_keywords.append(word)

    lower_response = ai_response.lower()

    mentioned = len(matched_keywords) > 3

    evidence_found = (
        "personal comment" in lower_response
        or "published content" in lower_response
        or (content.published_url and content.published_url in ai_response)
    )

    if "personal comment" in lower_response:
        citation_type = "personal_comment"
    elif content.published_url and content.published_url in ai_response:
        citation_type = "published_url"
    elif "published content" in lower_response:
        citation_type = "published_content"
    else:
        citation_type = "mention_only" if mentioned else "none"

    visibility_score = len(matched_keywords) * 10

    confidence_score = min(
        100,
        visibility_score + (40 if evidence_found else 0)
    )

    citation_test = CitationTest(
        property_id=content.property_id,
        content_id=content.id,
        platform=platform,
        query=test_query,
        prompt=test_query,
        target_brand=(
            content.property.brand_name
            if content.property and content.property.brand_name
            else None
        ),
        status="finished",
        last_run=datetime.now(timezone.utc),
        source_type=source_type,
        citation_target=citation_target,
        ai_response=ai_response,
        mentioned=mentioned,
        evidence_found=evidence_found,
        citation_type=citation_type,
        confidence_score=confidence_score,
        visibility_score=visibility_score,
        matched_keywords=", ".join(matched_keywords)
    )

    db.add(citation_test)

    db.commit()

    db.refresh(citation_test)

    citation_result = CitationResult(
        citation_test_id=citation_test.id,
        model=platform,
        mentioned=mentioned,
        rank=None,
        response=ai_response,
    )

    db.add(citation_result)
    db.commit()

    content.citation_count = (content.citation_count or 0) + (
        1 if evidence_found else 0
    )
    content.visibility_score = confidence_score
    db.commit()

    create_history_event(
        db=db,
        event_type="citation_test_finished",
        property_id=content.property_id,
        content_id=content.id,
        source_type=source_type,
        status=citation_type,
        summary=(
            f"Citation test: {citation_type}, "
            f"confidence {confidence_score}"
        ),
        details=ai_response[:500]
    )

    if evidence_found:
        create_history_event(
            db=db,
            event_type="citation_found",
            property_id=content.property_id,
            content_id=content.id,
            summary=f"Citation found for {article_title}",
            details=ai_response[:500]
        )

    return citation_test
