from datetime import datetime, timezone
import json
import re
import time

from sqlalchemy.orm import Session

from app.core.llm_provider import normalize_llm_provider
from app.providers import ProviderManager

from app.models.content import Content
from app.models.citation_test import CitationTest
from app.models.citation_result import CitationResult
from app.models.citation_test_run import CitationTestRun
from app.models.citation_test_result import CitationTestResult
from app.repositories.history_repository import (
    create_history_event
)
from app.utils.title_extractor import (
    extract_article_title
)


SUPPORTED_PROMPT_MODELS = {
    "chatgpt",
    "openai",
    "gpt-4.1-mini",
    "perplexity",
}

EXECUTABLE_CITATION_PROVIDERS = {
    "chatgpt",
    "perplexity",
}


def run_prompt_citation_test(
    db: Session,
    property_id: int,
    prompt: str,
    models: list[str],
    provider: str | None = None,
    providers: list[str] | None = None,
):
    from app.services.property_service import get_property

    property_record = get_property(db, property_id)

    if not property_record:
        return None

    target_brand = property_record.brand_name or property_record.name
    normalized_providers = normalize_citation_providers(
        providers=providers,
        models=models,
        provider=provider,
    )

    citation_run = CitationTestRun(
        property_id=property_id,
        prompt=prompt,
        target_brand=target_brand,
        provider=normalized_providers[0],
        status="processing",
    )

    db.add(citation_run)
    db.commit()
    db.refresh(citation_run)

    create_history_event(
        db=db,
        event_type="citation_test_started",
        property_id=property_id,
        citation_test_run_id=citation_run.id,
        status="processing",
        summary=f"Citation test started: {prompt[:120]}",
        details=prompt,
    )

    for provider_name in normalized_providers:
        result = execute_prompt_model(
            prompt=prompt,
            model_name=provider_name,
            target_brand=target_brand,
            domain=property_record.domain,
            provider=provider_name,
        )
        db.add(
            CitationTestResult(
                run_id=citation_run.id,
                model=provider_label(provider_name),
                provider=provider_name,
                status=result["status"],
                mentioned=result["mentioned"],
                rank=result["rank"],
                response_snippet=result["response_snippet"],
                raw_response=result["raw_response"],
                citations_json=json.dumps(result["citations"]),
                latency_ms=result["latency_ms"],
                error_message=result["error_message"],
            )
        )

    citation_run.status = "finished"
    citation_run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(citation_run)

    create_history_event(
        db=db,
        event_type="citation_test_finished",
        property_id=property_id,
        citation_test_run_id=citation_run.id,
        status="finished",
        summary=f"Citation test finished: {prompt[:120]}",
        details=serialize_run_preview(citation_run),
    )

    return citation_run


def normalize_citation_providers(
    *,
    providers: list[str] | None,
    models: list[str] | None,
    provider: str | None,
) -> list[str]:
    requested = providers or models or ([provider] if provider else ["chatgpt"])
    normalized = []

    for item in requested:
        provider_name = provider_from_label(item)

        if provider_name not in EXECUTABLE_CITATION_PROVIDERS:
            continue

        if provider_name not in normalized:
            normalized.append(provider_name)

    if not normalized:
        normalized.append(normalize_llm_provider(provider))

    return normalized


def dedupe_models(models: list[str]):
    if not models:
        return ["ChatGPT"]

    seen = set()
    deduped = []

    for model_name in models:
        normalized = model_name.strip()

        if not normalized or normalized.lower() in seen:
            continue

        seen.add(normalized.lower())
        deduped.append(normalized)

    return deduped or ["ChatGPT"]


def execute_prompt_model(
    prompt: str,
    model_name: str,
    target_brand: str,
    domain: str,
    provider: str | None = None,
):
    normalized_model = provider_from_label(model_name)

    if normalized_model not in SUPPORTED_PROMPT_MODELS:
        error = (
            f"{model_name} citation testing is not configured. "
            "Add the provider API integration before running this model."
        )

        return {
            "status": "failed",
            "mentioned": False,
            "rank": None,
            "response_snippet": error,
            "raw_response": error,
            "error_message": error,
        }

    provider_name = normalize_llm_provider(provider or normalized_model)
    provider_engine = ProviderManager.get_provider(provider_name)
    started_at = time.perf_counter()

    try:
        raw_response = provider_engine.run_citation_test(
            system_prompt=(
                "Answer the user's prompt naturally. Do not force a "
                "brand mention. If a website or brand is relevant, mention "
                "it in the same way a normal AI answer would."
            ),
            user_prompt=prompt,
            model="gpt-4.1-mini",
            temperature=0.4,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
    except Exception as error:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        message = str(error)

        return {
            "status": "failed",
            "mentioned": False,
            "rank": None,
            "response_snippet": message,
            "raw_response": "",
            "citations": [],
            "latency_ms": latency_ms,
            "error_message": message,
        }

    citations = extract_citations(raw_response)
    mentioned = detect_mention(
        response_text=raw_response,
        target_brand=target_brand,
        domain=domain,
    )

    return {
        "status": "finished",
        "mentioned": mentioned,
        "rank": detect_rank(
            response_text=raw_response,
            target_brand=target_brand,
            domain=domain,
        ) if mentioned else None,
        "response_snippet": build_response_snippet(
            response_text=raw_response,
            target_brand=target_brand,
            domain=domain,
        ),
        "raw_response": raw_response,
        "citations": citations,
        "latency_ms": latency_ms,
        "error_message": None,
    }


def provider_from_label(value: str | None):
    normalized = (value or "chatgpt").strip().lower()

    aliases = {
        "openai": "chatgpt",
        "gpt-4.1-mini": "chatgpt",
        "gpt": "chatgpt",
        "chat gpt": "chatgpt",
        "chatgpt": "chatgpt",
        "perplexity": "perplexity",
        "perplexity web": "perplexity",
    }

    return aliases.get(normalized, normalized)


def provider_label(provider: str):
    labels = {
        "chatgpt": "ChatGPT",
        "perplexity": "Perplexity",
    }

    return labels.get(provider, provider)


def extract_citations(response_text: str):
    citations = []

    for url in re.findall(r"https?://[^\s)>\]]+", response_text or ""):
        clean_url = url.rstrip(".,;:")

        if clean_url not in citations:
            citations.append(clean_url)

    return citations


def detect_mention(
    response_text: str,
    target_brand: str,
    domain: str,
):
    haystack = response_text.lower()
    brand = (target_brand or "").lower()
    clean_domain = normalize_domain(domain)

    return bool(
        (brand and brand in haystack)
        or (clean_domain and clean_domain in haystack)
    )


def detect_rank(
    response_text: str,
    target_brand: str,
    domain: str,
):
    candidates = [
        re.escape(value)
        for value in [target_brand, normalize_domain(domain)]
        if value
    ]

    if not candidates:
        return None

    pattern = re.compile("|".join(candidates), re.IGNORECASE)
    match = pattern.search(response_text)

    if not match:
        return None

    before_match = response_text[:match.start()]
    list_markers = re.findall(r"(?:^|\n)\s*(\d+)[.)]", before_match)

    if list_markers:
        return int(list_markers[-1])

    return 1


def build_response_snippet(
    response_text: str,
    target_brand: str,
    domain: str,
):
    if not response_text:
        return ""

    lowered = response_text.lower()
    needles = [
        (target_brand or "").lower(),
        normalize_domain(domain),
    ]
    positions = [
        lowered.find(needle)
        for needle in needles
        if needle and lowered.find(needle) >= 0
    ]

    if not positions:
        return response_text[:320]

    center = min(positions)
    start = max(0, center - 120)
    end = min(len(response_text), center + 220)

    return response_text[start:end]


def normalize_domain(domain: str | None):
    if not domain:
        return ""

    return (
        domain.lower()
        .replace("https://", "")
        .replace("http://", "")
        .strip("/")
    )


def serialize_run_preview(citation_run: CitationTestRun):
    return "\n".join(
        f"{result.provider}: {result.status}, mentioned={result.mentioned}, "
        f"rank={result.rank or '-'}, latency={result.latency_ms or '-'}ms"
        for result in citation_run.results
    )


def run_citation_test(
    db: Session,
    content_id: int,
    platform: str = "openai",
    source_type: str = "published_content",
    property_id: int | None = None,
    provider: str | None = None,
):
    normalized_provider = normalize_llm_provider(provider)

    query = db.query(Content).filter(Content.id == content_id)

    if property_id is not None:
        query = query.filter(Content.property_id == property_id)

    content = query.first()

    if not content:
        return None

    article_title = extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )

    test_query = (
        f"What do people say about {article_title}? "
        "Mention useful sources if you know them."
    )

    citation_target = content.published_url or article_title

    create_history_event(
        db=db,
        event_type="citation_test_started",
        property_id=content.property_id,
        content_id=content.id,
        summary=f"Citation test started for {article_title}",
        details=test_query,
    )

    if source_type == "personal_comment":
        context_message = f"""
Personal comment to evaluate as a possible citation source:

{content.body[:1200]}

When answering, only cite or attribute this comment if it is relevant.
"""
    else:
        context_message = f"""
Published content to evaluate as a possible citation source:

Title: {article_title}
URL: {content.published_url or "not published yet"}
Excerpt:
{content.body[:1200]}
"""

    provider_engine = ProviderManager.get_provider(normalized_provider)
    ai_response = provider_engine.generate_messages(
        messages=[
            {
                "role": "system",
                "content": """
You are an AI assistant helping users answer questions.

Give natural recommendation-style answers.
When citing source material, name whether it is a public source,
published content, or a personal comment.
"""
            },
            {
                "role": "user",
                "content": context_message
            },
            {
                "role": "user",
                "content": test_query
            }
        ],
        model="gpt-4.1-mini",
        temperature=0.7
    )

    matched_keywords = []

    title_words = article_title.lower().split()

    for word in title_words:

        if word in ai_response.lower():

            matched_keywords.append(word)

    lower_response = ai_response.lower()

    mentioned = len(matched_keywords) > 3

    evidence_found = (
        "personal comment" in lower_response
        or "published content" in lower_response
        or (content.published_url and content.published_url in ai_response)
    )

    if "personal comment" in lower_response:
        citation_type = "personal_comment"
    elif content.published_url and content.published_url in ai_response:
        citation_type = "published_url"
    elif "published content" in lower_response:
        citation_type = "published_content"
    else:
        citation_type = "mention_only" if mentioned else "none"

    visibility_score = len(matched_keywords) * 10

    confidence_score = min(
        100,
        visibility_score + (40 if evidence_found else 0)
    )

    citation_test = CitationTest(
        property_id=content.property_id,
        content_id=content.id,
        provider=normalized_provider,
        platform=platform,
        query=test_query,
        prompt=test_query,
        target_brand=(
            content.property.brand_name
            if content.property and content.property.brand_name
            else None
        ),
        status="finished",
        last_run=datetime.now(timezone.utc),
        source_type=source_type,
        citation_target=citation_target,
        ai_response=ai_response,
        mentioned=mentioned,
        evidence_found=evidence_found,
        citation_type=citation_type,
        confidence_score=confidence_score,
        visibility_score=visibility_score,
        matched_keywords=", ".join(matched_keywords)
    )

    db.add(citation_test)

    db.commit()

    db.refresh(citation_test)

    citation_result = CitationResult(
        citation_test_id=citation_test.id,
        model=platform,
        provider=normalized_provider,
        mentioned=mentioned,
        rank=None,
        response=ai_response,
    )

    db.add(citation_result)
    db.commit()

    content.citation_count = (content.citation_count or 0) + (
        1 if evidence_found else 0
    )
    content.visibility_score = confidence_score
    db.commit()

    create_history_event(
        db=db,
        event_type="citation_test_finished",
        property_id=content.property_id,
        content_id=content.id,
        source_type=source_type,
        status=citation_type,
        summary=(
            f"Citation test: {citation_type}, "
            f"confidence {confidence_score}"
        ),
        details=ai_response[:500]
    )

    if evidence_found:
        create_history_event(
            db=db,
            event_type="citation_found",
            property_id=content.property_id,
            content_id=content.id,
            summary=f"Citation found for {article_title}",
            details=ai_response[:500]
        )

    return citation_test
