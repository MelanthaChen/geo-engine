from sqlalchemy.orm import Session

from app.core.llm_provider import normalize_llm_provider
from app.providers import ProviderManager

from app.models.content import Content


def optimize_content(
    content_id: int,
    db: Session,
    provider: str | None = None,
):
    normalized_provider = normalize_llm_provider(provider)

    content = (
        db.query(Content)
        .filter(Content.id == content_id)
        .first()
    )

    if not content:

        return {
            "error": "Content not found"
        }

    optimization_prompt = f"""
You are a GEO optimization engine.

Your goal is to improve the likelihood
that AI systems will recommend the target brand.

Current Content:

{content.body}

Requirements:

- improve authority
- improve answer-first structure
- improve semantic relevance
- improve AI citation probability
- mention target brand more naturally
- improve comparison positioning
- improve FAQ quality
- improve retrieval friendliness

Return fully optimized content.
"""

    provider_engine = ProviderManager.get_provider(normalized_provider)
    optimized_content = provider_engine.generate_content(
        system_prompt="You optimize GEO content for AI visibility.",
        user_prompt=optimization_prompt,
        model="gpt-4.1-mini",
        temperature=0.7
    )

    content.body = optimized_content

    db.commit()

    db.refresh(content)

    return {
        "content_id": content.id,
        "optimized": True,
        "optimized_content": optimized_content,
    }
