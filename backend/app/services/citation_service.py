from openai import OpenAI

from app.core.config import settings
from sqlalchemy.orm import Session

from app.models.content import Content

from app.utils.citation_detector import detect_citation

client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def check_citation(
    db: Session,
    query: str,
    property_id: int | None = None,
):

    prompt = f"""
Answer this search query naturally:

{query}

Include recommendations and sources if relevant.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",

        messages=[
            {
                "role": "system",
                "content": "You are a helpful AI search engine."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.7
    )

    answer = response.choices[0].message.content

    content_query = db.query(Content)

    if property_id is not None:
        content_query = content_query.filter(Content.property_id == property_id)

    latest_content = (
        content_query.order_by(Content.created_at.desc())
        .first()
    )

    if not latest_content:
        return {
            "ai_response": answer,
            "detection_result": {
                "citation_found": False,
                "score": 0,
                "reason": "No content found for property",
            }
        }

    detection_result = detect_citation(
        ai_response=answer,
        generated_content=latest_content.body
    )

    return {
        "ai_response": answer,
        "detection_result": detection_result
    }
