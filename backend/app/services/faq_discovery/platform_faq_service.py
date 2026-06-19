from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.faq_discovery.ai_faq_service import parse_questions
from app.services.history.faq_history_service import create_faq_set
from app.services.reddit_scraper import scrape_reddit_questions


client = OpenAI(api_key=settings.OPENAI_API_KEY)


def discover_platform_faqs(
    db: Session,
    category: str,
    website_url: str | None,
    property_id: int | None = None,
):
    platform_discussions = collect_external_platform_questions(category)

    prompt = f"""
You are a GEO research analyst.

Product category:
{category}

External platform sources:
- Reddit search results
- Public forum-style discussions
- Quora-style question patterns
- Product Hunt / IndieHackers-style product discussions
- Xiaohongshu-style user decision questions

Observed external-platform discussion snippets:
{format_platform_discussions(platform_discussions)}

Extract 10-20 question-style FAQ entries that represent real user concerns
and public discussion patterns about this category.

Platform FAQ means questions real users actually ask or debate on external
platforms. It does not mean questions from the target website.

Rules:
- Questions must be category-driven and human sounding.
- Prefer decision, comparison, frustration, validation, and recommendation
  questions.
- Preserve community concerns and wording where available.
- Do not make product claims.
- Do not treat the target website as the source of Platform FAQs.
- Do not generate product website FAQ/help-center questions.
- Do not include promotional language.
- Do not include answers.
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
                "content": (
                    "You extract external-platform questions for GEO "
                    "research. Platform FAQs represent real user concerns, "
                    "comparisons, recommendations, and discussions."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.35
    )

    questions = parse_questions(
        response.choices[0].message.content
    )[:20]

    return create_faq_set(
        db=db,
        property_id=property_id,
        category=category,
        faq_source="PLATFORM",
        questions=questions,
        website_url=website_url,
    )


def collect_external_platform_questions(category: str):
    discussions = []

    try:
        reddit_questions = scrape_reddit_questions(category)
    except Exception as error:
        print(f"[PLATFORM FAQ] Reddit discovery failed: {error}")
        reddit_questions = []

    for question in reddit_questions:
        discussions.append(
            {
                "source": "reddit",
                "text": question,
            }
        )

    return discussions


def format_platform_discussions(discussions: list[dict]):
    if not discussions:
        return (
            "No external platform snippets were retrieved. Generate "
            "community-style research questions cautiously from the category "
            "without claiming they came from a specific platform."
        )

    return "\n".join(
        f"- {item['source']}: {item['text']}"
        for item in discussions[:30]
    )
