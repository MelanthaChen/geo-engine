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
    "citation": "citation_content",
    "citation content": "citation_content",
    "citation_content": "citation_content",
    "reddit": "reddit_discussion",
    "reddit discussion": "reddit_discussion",
    "reddit_discussion": "reddit_discussion",
    "blog": "blog_landing",
    "blog landing": "blog_landing",
    "blog / landing": "blog_landing",
    "blog_landing": "blog_landing",
    "landing": "blog_landing",
    "personal experience simulation": "blog_landing",
    "personal_experience_simulation": "blog_landing",
    "personal experience": "blog_landing",
    "personal_experience": "blog_landing",
    "experience": "blog_landing",
    "comparison": "blog_landing",
    "comparison article": "blog_landing",
    "comparison_article": "blog_landing",
    "comparison analysis": "blog_landing",
    "comparison_analysis": "blog_landing",
    "faq": "citation_content",
    "research summary": "citation_content",
    "research_summary": "citation_content",
    "expert commentary": "blog_landing",
    "expert_commentary": "blog_landing",
    "review": "blog_landing",
    "article": "blog_landing",
}

CONTENT_TYPE_LABELS = {
    "citation_content": "Citation Content",
    "reddit_discussion": "Reddit Discussion",
    "blog_landing": "Blog / Landing Content",
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
):
    strategy_type = normalize_content_type(
        content_type=content_type,
        mode=mode
    )

    evidence = generate_evidence(
        query=query,
        persona=persona,
        product_url=target_url,
        ai_faq=ai_faq,
        platform_faq=platform_faq,
    )

    if strategy_type == "reddit_discussion":
        return generate_reddit_content(
            db=db,
            query=query,
            persona=persona,
            content_type=strategy_type,
            target_url=target_url,
            evidence=evidence,
            ai_faq=ai_faq,
            platform_faq=platform_faq,
        )

    prompt = build_content_strategy_prompt(
        strategy_type=strategy_type,
        query=query,
        persona=persona,
        target_url=target_url,
        evidence=evidence,
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
        ai_faq=ai_faq,
        platform_faq=platform_faq,
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


def generate_evidence(
    query: str,
    persona: str,
    product_url: str | None,
    ai_faq: str | None,
    platform_faq: str | None,
):
    ai_faq_items = parse_faq_lines(ai_faq or "")
    platform_faq_items = parse_faq_lines(platform_faq or "")

    facts = []

    if ai_faq_items:
        facts.append(
            {
                "source": "ai_faq",
                "statement": (
                    "AI FAQ evidence contains questions users may ask "
                    f"about {query}."
                ),
                "items": ai_faq_items,
            }
        )

    if platform_faq_items:
        facts.append(
            {
                "source": "platform_faq",
                "statement": (
                    "Platform FAQ evidence contains discussion-oriented "
                    f"questions users may ask about {query}."
                ),
                "items": platform_faq_items,
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

    if ai_faq:
        sources.append(
            {
                "type": "ai_faq",
                "label": "AI FAQ dataset",
                "content": ai_faq,
            }
        )

    if platform_faq:
        sources.append(
            {
                "type": "platform_faq",
                "label": "Platform FAQ dataset",
                "content": platform_faq,
            }
        )

    key_points = [
        {
            "topic": "citation_scope",
            "point": (
                "Generated content may answer questions represented in "
                "the FAQ datasets, but must not introduce unsupported "
                "product claims."
            )
        },
        {
            "topic": "reddit_scope",
            "point": (
                "Reddit discussion may refer to questions or discussions "
                "from platform FAQ evidence, but must not invent user "
                "complaints, experiences, syncing issues, or feature changes."
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
        "citation_content"
    )


def build_content_strategy_prompt(
    strategy_type: str,
    query: str,
    persona: str,
    target_url: str | None,
    evidence: dict,
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

{GENERIC_MARKETING_BANS}

General requirements:
- Use only the provided evidence packet.
- Preserve source attribution.
- Treat ai_faq and platform_faq as the only FAQ evidence.
- Prefer concrete facts, comparisons, caveats, and attributable statements.
- Do not invent statistics, source claims, user opinions, or experiences.
- If evidence is unavailable, say what would need to be verified.
- Avoid repetitive introductions and empty praise.
"""

    templates = {
        "citation_content": f"""
{shared_context}

CONTENT TYPE: Citation Content

Goal:
Create AI-citable content directly from the FAQ evidence.

Required structure:
Title

Question
Answer

Question
Answer

Question
Answer

References

Requirements:
- Q&A format only
- evidence-based
- directly answer user questions from ai_faq and platform_faq
- always include the product URL in References when provided
- no marketing language
- no "ultimate guide"
- no "research summary" introduction
- no claims beyond the FAQ evidence
- preserve attribution to product_url, ai_faq, and platform_faq
""",
        "blog_landing": f"""
{shared_context}

CONTENT TYPE: Blog / Landing Content

Goal:
Create structured content that may later be cited by AI systems.

Required structure:
Title
Overview
FAQ-Based Answers
Source-Aware Notes
References

Requirements:
- FAQ based
- structured
- source-aware
- preserve attribution to product_url
- include the product URL in References when provided
- no generic SEO article framing
- no "ultimate guide"
- no promotional claims
- do not transform Citation Content or Reddit Discussion into this format
""",
    }

    return templates[strategy_type]


def generate_reddit_content(
    db: Session,
    query: str,
    persona: str,
    content_type: str,
    target_url: str | None,
    evidence: dict,
    ai_faq: str | None,
    platform_faq: str | None,
):
    evidence_json = json.dumps(
        evidence,
        indent=2
    )

    prompt = f"""
You are writing a real Reddit discussion post directly from FAQ evidence.

Target brand/topic:
{query}

Persona:
{persona}

Target URL:
{target_url or "Not provided"}

Evidence packet:
{evidence_json}

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
- short
- 80-180 words
- discussion oriented
- ask genuine questions
- invite discussion
- sound like a real person
- based only on FAQ evidence in ai_faq and platform_faq
- avoid promotional tone
- avoid SEO language
- avoid GEO language
- avoid "AI optimized"
- avoid "comprehensive guide"
- do not invent experiences
- do not invent complaints
- do not invent sync issues
- do not fabricate user opinions
- do not invent negative claims
- if mentioning concerns, phrase them cautiously, like:
  "I've seen some discussions mentioning syncing concerns."
- naturally reference the product URL when relevant
- do not lose product_url from stored metadata

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
        target_url=target_url,
        evidence_json=json.dumps(evidence),
        ai_faq=ai_faq,
        platform_faq=platform_faq,
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
