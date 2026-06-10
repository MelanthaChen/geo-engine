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

CONTENT_TYPE_ALIASES = {
    "reddit": "reddit_discussion",
    "reddit discussion": "reddit_discussion",
    "reddit_discussion": "reddit_discussion",
    "personal experience": "personal_experience",
    "personal_experience": "personal_experience",
    "experience": "personal_experience",
    "comparison": "comparison_analysis",
    "comparison analysis": "comparison_analysis",
    "comparison_analysis": "comparison_analysis",
    "faq": "faq",
    "research summary": "research_summary",
    "research_summary": "research_summary",
    "expert commentary": "expert_commentary",
    "expert_commentary": "expert_commentary",
    "review": "personal_experience",
    "article": "research_summary",
    "blog": "research_summary",
}

CONTENT_TYPE_LABELS = {
    "reddit_discussion": "Reddit Discussion",
    "personal_experience": "Personal Experience",
    "comparison_analysis": "Comparison Analysis",
    "faq": "FAQ",
    "research_summary": "Research Summary",
    "expert_commentary": "Expert Commentary",
}

GENERIC_MARKETING_BANS = """
Never use generic marketing or SEO language such as:
- Ultimate Guide
- Comprehensive Guide
- AI Optimized Guide
- SEO optimized
- GEO optimized
- keyword-rich
- unlock productivity
- game changer

The goal is citation-worthy information gain, not promotion.
"""


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
    strategy_type = normalize_content_type(
        content_type=content_type,
        mode=mode
    )

    if strategy_type == "reddit_discussion":
        return generate_reddit_content(
            db=db,
            query=query,
            persona=persona,
            content_type=strategy_type,
        )

    prompt = build_content_strategy_prompt(
        strategy_type=strategy_type,
        query=query,
        persona=persona,
        target_url=target_url,
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate evidence-rich, citation-worthy content "
                    "for AI retrieval and human research workflows."
                )
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

    article_title = extract_article_title(
        generated_content=generated_content,
        fallback=f"{CONTENT_TYPE_LABELS[strategy_type]}: {query}"
    )

    new_content = create_content(
        db=db,
        query_id=None,
        title=article_title,
        content_type=strategy_type,
        strategy_type=strategy_type,
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
        summary=(
            f"{CONTENT_TYPE_LABELS[strategy_type]} generated: "
            f"{article_title}"
        ),
        details=generated_content[:500]
    )

    return new_content


def normalize_content_type(
    content_type: str,
    mode: str,
):
    if mode == "reddit":
        return "reddit_discussion"

    normalized_key = (
        content_type
        .strip()
        .lower()
        .replace("-", "_")
    )

    return CONTENT_TYPE_ALIASES.get(
        normalized_key,
        "research_summary"
    )


def build_content_strategy_prompt(
    strategy_type: str,
    query: str,
    persona: str,
    target_url: str | None,
):
    shared_context = f"""
Target brand/topic:
{query}

Audience/persona:
{persona}

Target URL, if relevant:
{target_url or "Not provided"}

{GENERIC_MARKETING_BANS}

General requirements:
- Prefer concrete facts, comparisons, caveats, and attributable statements.
- Do not invent statistics or source claims.
- If evidence is unavailable, say what would need to be verified.
- Avoid repetitive introductions and empty praise.
"""

    templates = {
        "personal_experience": f"""
{shared_context}

CONTENT TYPE: Personal Experience

Goal:
Generate an experience report that could help another person understand
real workflow tradeoffs.

Required structure:
Title
Workflow
Specific Examples
Outcomes
Tradeoffs
What I Would Verify Next

Requirements:
- first-person voice
- describe workflow
- describe outcomes
- describe tradeoffs
- avoid unsupported claims
- include specific examples
- do not pretend to have used features that are not provided by context
""",
        "comparison_analysis": f"""
{shared_context}

CONTENT TYPE: Comparison Analysis

Goal:
Generate citation-friendly comparison content.

Required structure:
Title
Overview
Comparison Table
Pros
Cons
Recommendations
Evidence

Requirements:
- compare concrete dimensions, not vague marketing categories
- include tradeoffs and decision criteria
- use cautious language for claims that need source verification
- include an Evidence section with available facts and verification gaps
""",
        "faq": f"""
{shared_context}

CONTENT TYPE: FAQ

Goal:
Generate AI-extractable answers.

Format:
Question
Answer

Question
Answer

Question
Answer

Requirements:
- no long introduction
- concise answer-first responses
- answer concrete user questions
- include caveats where facts may depend on version, device, or plan
- do not include metadata labels beyond Question and Answer
""",
        "research_summary": f"""
{shared_context}

CONTENT TYPE: Research Summary

Goal:
Generate highly citable information.

Required structure:
Title
Key Findings
Statistics
Sources
Limitations
Open Questions

Requirements:
- summarize findings
- include statistics only when available or clearly marked as needing verification
- include a Sources section
- include a Limitations section
- distinguish observed facts from interpretation
""",
        "expert_commentary": f"""
{shared_context}

CONTENT TYPE: Expert Commentary

Goal:
Generate opinion plus reasoning.

Required structure:
Title
Claim
Supporting Evidence
Counterargument
Conclusion

Requirements:
- make one clear claim
- support it with evidence or careful reasoning
- include a real counterargument
- avoid unsupported negative claims
- keep the tone analytical rather than promotional
""",
    }

    return templates[strategy_type]


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
  "title": "...",
  "body": "..."
}}

Rules for title:
- natural Reddit-style question or discussion title
- no clickbait
- no marketing language
- no "AI optimized"
- no "comprehensive guide"

Rules for body:
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
        content_type="reddit_discussion",
        strategy_type="reddit_discussion",
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
        payload.get("title")
        or payload.get("reddit_title")
        or ""
    ).strip()

    reddit_body = str(
        payload.get("body")
        or payload.get("reddit_body")
        or ""
    ).strip()

    if not reddit_title or not reddit_body:
        raise ValueError(
            "Reddit content JSON must include title and body"
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
