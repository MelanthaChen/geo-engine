from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.content_repository import (create_content, get_all_contents)


def fetch_all_contents(db: Session):

    return get_all_contents(db)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_content(
    db: Session,
    query: str,
    persona: str,
    content_type: str,
):

    prompt = f"""
You are a GEO (Generative Engine Optimization) content strategist.

Generate high-quality AI-friendly content.

Query:
{query}

Persona:
{persona}

Content Type:
{content_type}

Requirements:

- answer-first structure
- highly informative
- semantic keyword rich
- optimized for AI retrieval
- natural authoritative tone
- include FAQ section
- include summary
- optimized for future AI citation

Return:

1. Title
2. Summary
3. Full Article
4. SEO Keywords
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert GEO content generation engine."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    generated_content = response.choices[0].message.content

    create_content(
    db=db,
    query_id=1,
    title=query,
    content_type=content_type,
    body=generated_content,
    target_persona=persona,
)

    return generated_content