from app.core.llm_provider import normalize_llm_provider
from app.providers import ProviderManager
from sqlalchemy.orm import Session

from app.models.content import Content

from app.utils.citation_detector import detect_citation


def check_citation(
    db: Session,
    query: str,
    property_id: int | None = None,
    provider: str | None = None,
):
    normalized_provider = normalize_llm_provider(provider)

    prompt = f"""
Answer this search query naturally:

{query}

Include recommendations and sources if relevant.
"""

    provider_engine = ProviderManager.get_provider(normalized_provider)
    answer = provider_engine.run_citation_test(
        system_prompt="You are a helpful AI search engine.",
        user_prompt=prompt,
        model="gpt-4.1-mini",
        temperature=0.7
    )

    content_query = db.query(Content)

    if property_id is not None:
        content_query = content_query.filter(Content.property_id == property_id)

    latest_content = (
        content_query.order_by(Content.created_at.desc())
        .first()
    )

    if not latest_content:
        return {
            "provider": normalized_provider,
            "ai_response": answer,
            "detection_result": {
                "citation_found": False,
                "score": 0,
                "reason": "No content found for property",
            }
        }

    detection_result = detect_citation(
        ai_response=answer,
        generated_content=latest_content.body
    )

    return {
        "provider": normalized_provider,
        "ai_response": answer,
        "detection_result": detection_result
    }
