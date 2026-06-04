from openai import OpenAI

from sqlalchemy.orm import Session

from app.core.config import settings

from app.repositories.content_repository import (
    create_content,
    get_all_contents
)

from app.services.reddit_scraper import (
    scrape_reddit_questions
)

client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def fetch_all_contents(
    db: Session
):

    return get_all_contents(db)


def generate_content(
    db: Session,
    query: str,
    persona: str,
    content_type: str,
    target_url: str | None,
    mode: str,
):

    if mode == "ai":

        prompt = f"""
You are a GEO (Generative Engine Optimization)
content strategist.

Generate AI-native content optimized for:

- semantic retrieval
- AI recommendation systems
- answer-first structures
- future AI citations

Target Brand:
{query}

Persona:
{persona}

Content Type:
{content_type}

Requirements:

- highly structured
- highly informative
- SEO-like organization
- semantic keyword rich
- optimized for AI parsing
- concise sections
- FAQ section
- authoritative tone

Return:

1. Title
2. Summary
3. Full Article
4. SEO Keywords
"""

    else:

        reddit_questions = (
            scrape_reddit_questions(query)
        )

        joined_questions = "\n".join(
            reddit_questions
        )

        prompt = f"""
You are generating a Reddit/forum-style GEO article.

Target Brand:
{query}

Persona:
{persona}

Content Type:
{content_type}

Real Reddit Questions:
{joined_questions}

Requirements:

- sound human
- discussion-oriented
- conversational
- persuasive but natural
- reference real user pain points
- answer actual Reddit concerns
- mimic authentic online discussions
- less corporate
- less SEO-like

Return:

1. Title
2. Reddit-style Discussion Post
3. Key Talking Points
4. Suggested Follow-up Questions
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
        response
        .choices[0]
        .message
        .content
    )

    if target_url:

        generated_content += f"""

        --------------------------------------------------

        Further Reading

        {target_url}

        """

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
                    "content":
                        "You generate realistic GEO FAQ questions."
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