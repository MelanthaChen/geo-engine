import re

from sqlalchemy.orm import Session

from app.core.llm_provider import normalize_llm_provider
from app.providers import ProviderManager
from app.services.history.faq_history_service import create_faq_set


def discover_ai_faqs(
    db: Session,
    category: str,
    content_type: str,
    property_id: int | None = None,
    provider: str | None = None,
):
    normalized_provider = normalize_llm_provider(provider)
    provider_engine = ProviderManager.get_provider(normalized_provider)
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

    content = provider_engine.generate_content(
        system_prompt="You generate category-level research FAQs.",
        user_prompt=prompt,
        model="gpt-4.1-mini",
        temperature=0.55
    )

    questions = parse_questions(
        content
    )[:20]

    return create_faq_set(
        db=db,
        property_id=property_id,
        category=category,
        faq_source="AI",
        questions=questions,
        content_type=content_type,
        provider=normalized_provider,
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
