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

    latest_content = (
        db.query(Content)
        .order_by(Content.created_at.desc())
        .first()
    )

    detection_result = detect_citation(
        ai_response=answer,
        generated_content=latest_content.body
    )

    return {
        "ai_response": answer,
        "detection_result": detection_result
    }