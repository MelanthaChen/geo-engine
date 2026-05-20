from typing import List


def generate_queries(
    category: str,
    niche: str
) -> List[str]:

    queries = [

        f"best {niche}",

        f"{niche} for beginners",

        f"{niche} vs alternatives",

        f"safest {niche}",

        f"top rated {niche}",

        f"how to choose {niche}",

        f"best {niche} for small dogs",

        f"best {niche} for puppies"
    ]

    return queries