from openai import OpenAI

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.llm_provider import normalize_llm_provider

from app.models.content import Content


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def optimize_content(
    content_id: int,
    db: Session,
    provider: str | None = None,
):
    normalize_llm_provider(provider)

    content = (
        db.query(Content)
        .filter(Content.id == content_id)
        .first()
    )

    if not content:

        return {
            "error": "Content not found"
        }

    optimization_prompt = f"""
You are a GEO optimization engine.

Your goal is to improve the likelihood
that AI systems will recommend the target brand.

Current Content:

{content.body}

Requirements:

- improve authority
- improve answer-first structure
- improve semantic relevance
- improve AI citation probability
- mention target brand more naturally
- improve comparison positioning
- improve FAQ quality
- improve retrieval friendliness

Return fully optimized content.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You optimize GEO content for AI visibility."
            },
            {
                "role": "user",
                "content": optimization_prompt
            }
        ],
        temperature=0.7
    )

    optimized_content = (
        response
        .choices[0]
        .message
        .content
    )

    content.body = optimized_content

    db.commit()

    db.refresh(content)

    return {
        "content_id": content.id,
        "optimized": True,
        "optimized_content": optimized_content,
    }
