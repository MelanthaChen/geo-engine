from typing import List

from sqlalchemy.orm import Session

from openai import OpenAI

from app.core.config import OPENAI_API_KEY

from app.repositories.query_repository import create_query


client = OpenAI(
    api_key=OPENAI_API_KEY
)


def generate_queries(
    db: Session,
    category: str,
    niche: str
) -> List[str]:

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

    response = client.chat.completions.create(
        model="gpt-4.1-mini",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.8
    )

    content = response.choices[0].message.content

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