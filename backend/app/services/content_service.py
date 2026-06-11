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


CONTENT_TYPE_ALIASES = {
    "publishable article": "publishable_article",
    "publishable_article": "publishable_article",
    "article": "publishable_article",
    "citation": "publishable_article",
    "citation content": "publishable_article",
    "citation_content": "publishable_article",
    "reddit": "publishable_article",
    "reddit discussion": "publishable_article",
    "reddit_discussion": "publishable_article",
    "blog": "publishable_article",
    "blog landing": "publishable_article",
    "blog / landing": "publishable_article",
    "blog_landing": "publishable_article",
    "landing": "publishable_article",
    "personal experience simulation": "publishable_article",
    "personal_experience_simulation": "publishable_article",
    "personal experience": "publishable_article",
    "personal_experience": "publishable_article",
    "experience": "publishable_article",
    "comparison": "publishable_article",
    "comparison article": "publishable_article",
    "comparison_article": "publishable_article",
    "comparison analysis": "publishable_article",
    "comparison_analysis": "publishable_article",
    "faq": "publishable_article",
    "research summary": "publishable_article",
    "research_summary": "publishable_article",
    "expert commentary": "publishable_article",
    "expert_commentary": "publishable_article",
    "review": "publishable_article",
}

CONTENT_TYPE_LABELS = {
    "publishable_article": "Publishable Article",
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
    ai_faq: str | None = None,
    platform_faq: str | None = None,
    faq_source: str | None = None,
):
    normalized_faq_source = normalize_faq_source(
        faq_source=faq_source,
        mode=mode
    )

    strategy_type = normalize_content_type(
        content_type=content_type
    )

    evidence = generate_evidence(
        query=query,
        persona=persona,
        product_url=target_url,
        ai_faq=ai_faq,
        platform_faq=platform_faq,
        faq_source=normalized_faq_source,
    )

    prompt = build_content_strategy_prompt(
        strategy_type=strategy_type,
        query=query,
        persona=persona,
        target_url=target_url,
        evidence=evidence,
        faq_source=normalized_faq_source,
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
        target_url=target_url,
        evidence_json=json.dumps(evidence),
        ai_faq=ai_faq if normalized_faq_source == "ai_faq" else None,
        platform_faq=(
            platform_faq
            if normalized_faq_source == "platform_faq"
            else None
        ),
        faq_source=normalized_faq_source,
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
            f"{CONTENT_TYPE_LABELS[strategy_type]} "
            f"from {normalized_faq_source} generated: "
            f"{article_title}"
        ),
        details=generated_content[:500]
    )

    return new_content


def generate_evidence(
    query: str,
    persona: str,
    product_url: str | None,
    ai_faq: str | None,
    platform_faq: str | None,
    faq_source: str,
):
    ai_faq_items = parse_faq_lines(ai_faq or "")
    platform_faq_items = parse_faq_lines(platform_faq or "")
    selected_items = (
        ai_faq_items
        if faq_source == "ai_faq"
        else platform_faq_items
    )
    selected_faq = (
        ai_faq
        if faq_source == "ai_faq"
        else platform_faq
    )

    facts = []

    if selected_items:
        source_statement = (
            "AI FAQ evidence contains questions AI systems commonly answer "
            f"about {query}."
            if faq_source == "ai_faq"
            else (
                "Platform FAQ evidence contains user concerns, comparisons, "
                f"and discussion topics about {query}."
            )
        )

        facts.append(
            {
                "source": faq_source,
                "statement": source_statement,
                "items": selected_items,
            }
        )

    sources = [
        {
            "type": "product_url",
            "url": product_url,
            "note": (
                "Provided product URL. Preserve this attribution in "
                "citation and blog content."
            ),
        }
    ] if product_url else []

    if selected_faq:
        sources.append(
            {
                "type": faq_source,
                "label": (
                    "AI FAQ dataset"
                    if faq_source == "ai_faq"
                    else "Platform FAQ dataset"
                ),
                "content": selected_faq,
            }
        )

    key_points = [
        {
            "topic": "source_scope",
            "point": (
                f"Generated content must use only the {faq_source} dataset."
            )
        },
        {
            "topic": "content_scope",
            "point": (
                "Generated content should be a human-readable publishable "
                "article, not a FAQ dump or source transformation."
            )
        },
    ]

    return {
        "facts": facts,
        "sources": sources,
        "key_points": key_points,
    }


def parse_faq_lines(faq_text: str):
    lines = [
        line.strip()
        for line in faq_text.splitlines()
        if line.strip()
    ]

    cleaned_lines = []

    for line in lines:
        cleaned = re.sub(
            r"^\s*(?:[-*]|\d+[.)])\s*",
            "",
            line
        ).strip()

        if cleaned:
            cleaned_lines.append(cleaned)

    return cleaned_lines


def normalize_faq_source(
    faq_source: str | None,
    mode: str,
):
    normalized = (faq_source or "").strip().lower()

    if normalized in {"platform", "platform_faq", "community"}:
        return "platform_faq"

    if normalized in {"ai", "ai_faq"}:
        return "ai_faq"

    if mode in {"platform", "reddit"}:
        return "platform_faq"

    return "ai_faq"


def safe_scrape_reddit_questions(query: str):
    try:
        return scrape_reddit_questions(query)
    except Exception as error:
        print(f"[EVIDENCE MODE] Reddit scrape skipped: {error}")
        return []


def parse_evidence_payload(raw_content: str):
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
                "Evidence generation did not return JSON"
            )

        payload = json.loads(match.group(0))

    evidence = {
        "facts": payload.get("facts") or [],
        "sources": payload.get("sources") or [],
        "key_points": payload.get("key_points") or [],
    }

    for key in evidence:
        if not isinstance(evidence[key], list):
            evidence[key] = [evidence[key]]

    return evidence


def normalize_content_type(
    content_type: str,
):
    normalized_key = (
        content_type
        .strip()
        .lower()
        .replace("-", "_")
    )

    return CONTENT_TYPE_ALIASES.get(
        normalized_key,
        "publishable_article"
    )


def build_content_strategy_prompt(
    strategy_type: str,
    query: str,
    persona: str,
    target_url: str | None,
    evidence: dict,
    faq_source: str,
):
    evidence_json = json.dumps(
        evidence,
        indent=2
    )

    shared_context = f"""
Target brand/topic:
{query}

Audience/persona:
{persona}

Target URL, if relevant:
{target_url or "Not provided"}

Evidence packet:
{evidence_json}

FAQ source:
{faq_source}

{GENERIC_MARKETING_BANS}

General requirements:
- Use only the provided evidence packet.
- Preserve source attribution.
- Treat FAQ source and content type as independent concepts.
- Keep the content type identical regardless of FAQ source.
- Use only the selected FAQ source.
- Write 500-1000 words.
- Write natural human-readable prose.
- Include the target URL naturally when relevant.
- Do not use Question/Answer blocks.
- Do not dump the FAQ list.
- Do not include Key Findings, Research Summary, or SEO Keywords sections.
- Do not use "AI optimized" wording.
- Do not use "ultimate guide" wording.
- Do not invent facts beyond the selected FAQ source.
"""

    templates = {
        "publishable_article": f"""
{shared_context}

CONTENT TYPE: Publishable Article

Goal:
Create one full publishable content piece from the selected FAQ source.

Required structure:
Title
Human-readable article body
References

Source-specific guidance:
- If FAQ source is ai_faq, preserve questions AI systems commonly answer.
- If FAQ source is platform_faq, preserve user concerns, comparisons,
  discussions, and community interests.

Requirements:
- 500-1000 words
- publishable
- human sounding
- evidence-based
- no FAQ dump
- no Question/Answer blocks
- no Key Findings section
- no Research Summary section
- no SEO keyword section
- no AI optimized wording
- no generic marketing tone
- include the target URL naturally and in References when provided
""",
    }

    return templates[strategy_type]


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
