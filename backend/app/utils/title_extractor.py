import re


TITLE_PATTERNS = [
    r"^\s*#+\s+(.+?)\s*$",
    r"^\s*\*{0,2}\s*(?:\d+\.\s*)?Title\s*\*{0,2}\s*:\s*(.+?)\s*$",
    r"^\s*(?:\d+\.\s*)?Title\s*$\s*^\s*[\"“]?(.+?)[\"”]?\s*$",
]


def extract_article_title(
    generated_content: str,
    fallback: str,
) -> str:
    if not generated_content:
        return fallback

    lines = [
        line.strip()
        for line in generated_content.splitlines()
        if line.strip()
    ]

    preview = "\n".join(lines[:6])

    for pattern in TITLE_PATTERNS:
        match = re.search(
            pattern,
            preview,
            re.IGNORECASE | re.MULTILINE
        )

        if match:
            return clean_title(match.group(1)) or fallback

    first_line = clean_title(lines[0]) if lines else ""

    if first_line and len(first_line) <= 160:
        return first_line

    return fallback


def clean_title(title: str) -> str:
    title = title.strip()

    title = re.sub(
        r"^\s*\*{0,2}\s*(?:\d+\.\s*)?Title\s*\*{0,2}\s*:?\s*\*{0,2}\s*",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = title.strip().strip("*").strip().strip('"').strip("'").strip("“”")

    return title
