from typing import List

from openai import OpenAI

from app.core.config import OPENAI_API_KEY


client = OpenAI(
    api_key=OPENAI_API_KEY
)


def generate_queries(
    category: str,
    niche: str
) -> List[str]:

    prompt = f"""
You are a GEO (Generative Engine Optimization) query strategist.

Generate high-quality AI search queries for:

Category: {category}
Niche: {niche}

Generate:

- informational queries
- comparison queries
- purchase intent queries
- long-tail queries
- scenario-based queries

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

    return queries