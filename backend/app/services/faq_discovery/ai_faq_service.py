import re

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.history.faq_history_service import create_faq_set


client = OpenAI(api_key=settings.OPENAI_API_KEY)


def discover_ai_faqs(
    db: Session,
    category: str,
    content_type: str,
    property_id: int | None = None,
):
    prompt = f"""
You are an expert researcher.

Given a product category:

{category}

And a content type:

{content_type}

Generate 10-20 likely questions real users would ask about this category in:

- Google
- ChatGPT
- Perplexity
- Reddit

Rules:
- Category-driven, not brand-driven.
- Do not praise or promote a specific brand.
- Focus on discovery, comparison, buying criteria, trust, limitations,
  alternatives, common mistakes, workflows, and practical decision-making.
- Return ranked FAQs only.

Format:
1. Question
2. Question
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You generate category-level research FAQs."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.55
    )

    questions = parse_questions(
        response.choices[0].message.content
    )[:20]

    return create_faq_set(
        db=db,
        property_id=property_id,
        category=category,
        faq_source="AI",
        questions=questions,
        content_type=content_type,
    )


def parse_questions(raw_text: str):
    questions = []

    for line in raw_text.splitlines():
        question = re.sub(
            r"^\s*(?:[-*]|\d+[.)])\s*",
            "",
            line
        ).strip()

        if question and question.endswith("?"):
            questions.append(question)

    return questions
