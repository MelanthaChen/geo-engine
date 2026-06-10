from openai import OpenAI

import json
import re

from sqlalchemy.orm import Session

from app.core.config import settings

from app.repositories.content_repository import (
    create_content,
    get_all_contents
)
from app.repositories.history_repository import (
    create_history_event
)

from app.services.reddit_scraper import (
    scrape_reddit_questions
)
from app.utils.title_extractor import (
    extract_article_title
)

client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


REDDIT_FORBIDDEN_PATTERNS = [
    r"^\s*\d+\.\s+",
    r"^\s*title\s*:",
    r"^\s*summary\s*:",
    r"^\s*introduction\s*:",
    r"^\s*full article\s*:",
    r"^\s*faq\s*:",
    r"^\s*reddit-style discussion post\s*:",
    r"^\s*key talking points\s*:",
    r"^\s*suggested follow-up questions\s*:",
]

REDDIT_TERMINAL_METADATA_PATTERNS = [
    r"^\s*faq\s*:",
    r"^\s*key talking points\s*:",
    r"^\s*suggested follow-up questions\s*:",
    r"^\s*seo keywords\s*:",
]


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

    elif mode == "reddit":
        return generate_reddit_content(
            db=db,
            query=query,
            persona=persona,
            content_type=content_type,
        )

    else:
        return generate_reddit_content(
            db=db,
            query=query,
            persona=persona,
            content_type=content_type,
        )

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

    article_title = extract_article_title(
        generated_content=generated_content,
        fallback=query
    )

    new_content = create_content(
        db=db,
        query_id=None,
        title=article_title,
        content_type=content_type,
        body=generated_content,
        target_persona=persona,
        generation_mode=mode,
    )

    create_history_event(
        db=db,
        event_type="content_created",
        content_id=new_content.id,
        source_type=mode,
        status=new_content.publish_status,
        summary=f"{mode} {content_type} generated: {article_title}",
        details=generated_content[:500]
    )

    return new_content


def generate_reddit_content(
    db: Session,
    query: str,
    persona: str,
    content_type: str,
):
    reddit_questions = scrape_reddit_questions(query)

    joined_questions = "\n".join(reddit_questions[:12])

    prompt = f"""
You are writing a real Reddit text post from the point of view of a real person.

Target brand/topic:
{query}

Persona:
{persona}

Relevant community questions:
{joined_questions}

Return ONLY valid JSON with exactly these keys:
{{
  "reddit_title": "...",
  "reddit_body": "..."
}}

Rules for reddit_title:
- natural Reddit-style question or discussion title
- no clickbait
- no marketing language
- no "AI optimized"
- no "comprehensive guide"

Rules for reddit_body:
- ONLY the discussion post content
- 150-400 words
- first-person language
- ask genuine questions
- invite discussion
- sound like a real person
- avoid promotional tone
- avoid SEO language
- avoid GEO language
- avoid "AI optimized"
- avoid "comprehensive guide"
- do not invent negative claims
- if mentioning concerns, phrase them cautiously, like:
  "I've seen some people mention syncing issues. Has anyone experienced that?"

Never include:
- Title:
- Summary:
- Introduction:
- Full Article:
- FAQ:
- numbered sections
- Markdown document structure
- metadata labels
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write natural Reddit posts and return strict JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.8
    )

    raw_content = response.choices[0].message.content

    reddit_payload = parse_reddit_payload(raw_content)

    reddit_title = reddit_payload["reddit_title"]

    reddit_body = clean_reddit_body(
        reddit_payload["reddit_body"]
    )

    print("[REDDIT MODE] Generated title")
    print("[REDDIT MODE] Generated discussion body")

    new_content = create_content(
        db=db,
        query_id=None,
        title=reddit_title,
        content_type=content_type,
        body=reddit_body,
        target_persona=persona,
        generation_mode="reddit",
        reddit_title=reddit_title,
        reddit_body=reddit_body,
    )

    create_history_event(
        db=db,
        event_type="reddit_content_created",
        content_id=new_content.id,
        source_type="reddit",
        status=new_content.publish_status,
        summary=f"Reddit post generated: {reddit_title}",
        details=reddit_body[:500]
    )

    return new_content


def parse_reddit_payload(raw_content: str):
    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError:
        match = re.search(
            r"\{.*\}",
            raw_content,
            re.DOTALL
        )

        if not match:
            raise ValueError(
                "Reddit content generation did not return JSON"
            )

        payload = json.loads(match.group(0))

    reddit_title = str(
        payload.get("reddit_title", "")
    ).strip()

    reddit_body = str(
        payload.get("reddit_body", "")
    ).strip()

    if not reddit_title or not reddit_body:
        raise ValueError(
            "Reddit content JSON must include reddit_title and reddit_body"
        )

    return {
        "reddit_title": reddit_title,
        "reddit_body": reddit_body,
    }


def clean_reddit_body(reddit_body: str):
    cleaned_lines = []
    skip_remaining = False

    for line in reddit_body.splitlines():
        stripped = line.strip()

        if any(
            re.search(pattern, stripped, re.IGNORECASE)
            for pattern in REDDIT_TERMINAL_METADATA_PATTERNS
        ):
            skip_remaining = True
            continue

        if skip_remaining:
            continue

        if any(
            re.search(pattern, stripped, re.IGNORECASE)
            for pattern in REDDIT_FORBIDDEN_PATTERNS
        ):
            continue

        cleaned_lines.append(line)

    cleaned_body = "\n".join(cleaned_lines).strip()

    cleaned_body = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned_body
    )

    return cleaned_body


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
