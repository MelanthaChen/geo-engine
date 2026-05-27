from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.content_repository import (create_content, get_all_contents)

from app.services.reddit_scraper import (
    scrape_reddit_questions
)


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
                "content":
                "You are an expert GEO content generation engine."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    generated_content = (
        response.choices[0]
        .message
        .content
    )

    new_content = create_content(
        db=db,
        query_id=None,
        title=query,
        content_type=content_type,
        body=generated_content,
        target_persona=persona,
    )

    return new_content

def generate_faqs(
    target: str,
    mode: str,
):

    if mode == "ai":

        faq_prompt = f"""
You are a GEO FAQ discovery engine.

Based on your understanding of user behavior
and common discussions,

generate 15 highly realistic and commonly asked
questions about:

{target}

Requirements:

- questions should sound natural
- questions should feel like real user concerns
- focus on usage
- focus on comparisons
- focus on workflows
- focus on productivity
- focus on student / professional use cases
- mimic realistic online discussions

Return ONLY the questions.

Format:

1. ...
2. ...
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate realistic GEO FAQ questions."
                    )
                },
                {
                    "role": "user",
                    "content": faq_prompt
                }
            ],
            temperature=0.8
        )

        return response.choices[0].message.content

    else:

        reddit_questions = (
            scrape_reddit_questions(target)
        )

        return "\n".join([
            f"{idx + 1}. {question}"
            for idx, question in enumerate(
                reddit_questions
            )
        ])