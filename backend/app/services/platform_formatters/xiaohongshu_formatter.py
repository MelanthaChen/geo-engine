import json
import re

from app.models.content import Content
from app.services.platform_formatters.base import PlatformPost
from app.services.platform_formatters.reddit_formatter import (
    extract_discussion_topic,
    remove_article_title_noise,
    transform_article_to_reddit_body,
)


class XiaohongshuFormatter:
    platform = "xiaohongshu"
    formatter_name = "XiaohongshuFormatter"
    formatter_version = "1.0.0"

    def prepare(self, content: Content) -> PlatformPost:
        source_body = content.body or ""
        topic = extract_discussion_topic(content)
        structured_note = parse_xiaohongshu_note(source_body)

        if structured_note:
            title = structured_note.get(
                "title"
            ) or build_xiaohongshu_title(content=content, topic=topic)
            body = build_xiaohongshu_body_from_note(structured_note)
        else:
            title = build_xiaohongshu_title(content=content, topic=topic)
            body = build_xiaohongshu_body(
                content=content,
                topic=topic,
                source_body=source_body,
            )

        print(
            "[XIAOHONGSHU FORMATTER] source_body_chars="
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


def parse_xiaohongshu_note(source_body: str):
    try:
        parsed = json.loads(source_body)
    except Exception:
        return None

    if not isinstance(parsed, dict):
        return None

    if not any(key in parsed for key in {"title", "body", "hashtags", "cta"}):
        return None

    return parsed


def build_xiaohongshu_body_from_note(note: dict):
    hashtags = note.get("hashtags") or []

    if isinstance(hashtags, str):
        hashtags = [hashtags]

    normalized_hashtags = [
        hashtag if str(hashtag).startswith("#") else f"#{hashtag}"
        for hashtag in hashtags
        if str(hashtag).strip()
    ]

    body_parts = [
        note.get("body", ""),
        note.get("cta", ""),
        " ".join(normalized_hashtags),
    ]

    return "\n\n".join(
        str(part).strip()
        for part in body_parts
        if str(part).strip()
    )


def build_xiaohongshu_title(
    content: Content,
    topic: str,
):
    title = remove_article_title_noise(content.title or "")

    if not title:
        title = f"{topic}真实使用观察"

    title = re.sub(r"\s+", " ", title).strip()

    if len(title) > 48:
        title = title[:48].rsplit(" ", 1)[0].strip()

    return title or f"{topic}经验整理"


def build_xiaohongshu_body(
    content: Content,
    topic: str,
    source_body: str,
):
    cleaned_body = transform_article_to_reddit_body(source_body)
    hashtags = build_hashtags(
        topic=topic,
        content_type=content.content_type,
        persona=content.target_persona,
    )

    body_parts = [
        f"最近在整理关于 {topic} 的资料，发现有几个点很值得单独记下来。",
        cleaned_body.strip(),
        "如果你也在比较类似方案，可以先把自己的使用场景、预算和最在意的结果写清楚，再去看具体工具。",
        "你会优先看功能、价格，还是实际工作流里的稳定性？",
        " ".join(hashtags),
    ]

    return "\n\n".join(part for part in body_parts if part).strip()


def build_hashtags(
    topic: str,
    content_type: str | None,
    persona: str | None,
):
    raw_tags = [
        topic,
        content_type,
        persona,
        "工具对比",
        "效率工具",
    ]

    tags = []

    for raw_tag in raw_tags:
        tag = normalize_hashtag(raw_tag)

        if tag and tag not in tags:
            tags.append(tag)

    return tags[:6]


def normalize_hashtag(value: str | None):
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", value or "")

    if not cleaned:
        return ""

    return f"#{cleaned}"
