from typing import List

from sqlalchemy.orm import Session

from app.core.llm_provider import normalize_llm_provider
from app.providers import ProviderManager

from app.repositories.query_repository import create_query


def generate_queries(
    db: Session,
    category: str,
    niche: str,
    provider: str | None = None,
) -> List[str]:
    normalized_provider = normalize_llm_provider(provider)

    prompt = f"""
You are a GEO query strategist.

Generate high-quality AI search queries for:

Category: {category}
Niche: {niche}

Generate:

- informational queries
- comparison queries
- purchase intent queries
- long-tail queries
- scenario queries

Return ONLY a plain list.
One query per line.
"""

    provider_engine = ProviderManager.get_provider(normalized_provider)
    content = provider_engine.run_query(
        system_prompt=None,
        user_prompt=prompt,
        model="gpt-4.1-mini",
        temperature=0.8
    )

    queries = [
        line.strip("- ").strip()
        for line in content.split("\n")
        if line.strip()
    ]

    for query in queries:

        create_query(
            db=db,
            category=category,
            niche=niche,
            query_text=query
        )

    return queries
