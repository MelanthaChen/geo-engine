import re

from app.models.content import Content
from app.services.platform_formatters.base import PlatformPost


class RedditFormatter:
    platform = "reddit"
    formatter_name = "RedditFormatter"
    formatter_version = "1.0.0"

    def prepare(self, content: Content) -> PlatformPost:
        source_body = content.body or ""
        topic = extract_discussion_topic(content)
        cleaned_body = transform_article_to_reddit_body(source_body)
        title = build_reddit_title(content=content, topic=topic)
        body = build_reddit_body(
            topic=topic,
            transformed_body=cleaned_body,
        )

        print(
            "[REDDIT FORMATTER] source_body_chars="
            f"{len(source_body)} formatted_body_chars={len(body)} "
            f"formatted_title_chars={len(title)} "
            f"formatter_version={self.formatter_version}"
        )

        return PlatformPost(
            title=title,
            body=body,
            platform=self.platform,
            formatter_name=self.formatter_name,
            formatter_version=self.formatter_version,
        )


def build_reddit_title(
    content: Content,
    topic: str,
):
    title = normalize_title(content.title or "")

    if is_machine_title(title):
        return f"Has anyone looked closely at {topic}?"

    if title.endswith("?"):
        return title

    title = remove_article_title_noise(title)

    if not title:
        return f"Has anyone looked closely at {topic}?"

    return f"What do people think about {title}?"


def build_reddit_body(
    topic: str,
    transformed_body: str,
):
    opening = (
        f"I've been digging into {topic} and wanted to sanity-check the way "
        "I'm thinking about it. The writeup I have is fairly detailed, so "
        "I'm keeping the main points here instead of trying to turn it into a "
        "short hot take."
    )

    ending = (
        "What has everyone else's experience been? Would you frame any of "
        "these tradeoffs differently?"
    )

    body_parts = [
        opening,
        transformed_body.strip(),
        ending,
    ]

    return "\n\n".join(part for part in body_parts if part).strip()


def transform_article_to_reddit_body(source_body: str):
    lines = source_body.splitlines()
    transformed_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            transformed_lines.append("")
            continue

        if should_remove_metadata_line(stripped):
            continue

        transformed_lines.append(transform_heading(stripped))

    return collapse_excess_blank_lines("\n".join(transformed_lines)).strip()


def should_remove_metadata_line(line: str):
    normalized = line.lower()

    metadata_prefixes = (
        "title:",
        "summary:",
        "full article:",
        "reddit-style discussion post:",
    )

    return normalized.startswith(metadata_prefixes)


def transform_heading(line: str):
    if line.startswith("#"):
        heading = line.lstrip("#").strip()
        return f"**{heading}**"

    return line


def collapse_excess_blank_lines(value: str):
    return re.sub(r"\n{3,}", "\n\n", value)


def extract_discussion_topic(content: Content):
    candidates = [
        content.title or "",
        content.target_persona or "",
        content.content_type or "",
    ]

    for candidate in candidates:
        cleaned = remove_article_title_noise(candidate)

        if cleaned and len(cleaned) > 3:
            return cleaned

    return "this topic"


def is_machine_title(title: str):
    normalized = title.lower()

    if ":" in normalized and normalized.split(":", 1)[0] in {
        "comparison",
        "guide",
        "review",
        "discussion",
        "blog_post",
        "educational",
        "opinion",
        "case_study",
        "best_of",
        "alternatives",
    }:
        return True

    return normalized in {
        "comparison",
        "guide",
        "review",
        "discussion",
        "blog_post",
    }


def remove_article_title_noise(value: str):
    cleaned = normalize_title(value)
    cleaned = re.sub(
        r"^(comparison|guide|review|discussion|blog_post|educational|"
        r"opinion|case_study|best_of|alternatives):\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned.strip()


def normalize_title(value: str):
    cleaned = re.sub(r"\s+", " ", value or "").strip()

    if len(cleaned) > 220:
        cleaned = cleaned[:220].rsplit(" ", 1)[0].strip()

    return cleaned
