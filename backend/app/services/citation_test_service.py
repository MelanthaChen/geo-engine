from openai import OpenAI

from sqlalchemy.orm import Session

from app.core.config import settings

from app.models.content import Content
from app.models.citation_test import CitationTest


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def run_citation_test(
    db: Session,
    content_id: int,
    platform: str = "openai",
):

    content = db.query(Content).filter(
        Content.id == content_id
    ).first()

    if not content:
        return None

    test_query = content.title

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": """
You are an AI assistant helping users answer questions.

Give natural recommendation-style answers.
"""
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

    title_words = content.title.lower().split()

    for word in title_words:

        if word in ai_response.lower():

            matched_keywords.append(word)

    mentioned = len(matched_keywords) > 3

    visibility_score = len(matched_keywords) * 10

    citation_test = CitationTest(
        content_id=content.id,
        platform=platform,
        query=test_query,
        ai_response=ai_response,
        mentioned=mentioned,
        visibility_score=visibility_score,
        matched_keywords=", ".join(matched_keywords)
    )

    db.add(citation_test)

    db.commit()

    db.refresh(citation_test)

    return citation_test