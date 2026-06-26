import json
import re

from openai import OpenAI

from app.core.config import settings
from app.models.content import Content
from app.services.platform_formatters.base import PlatformPost


class RedditFormatter:
    platform = "reddit"

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def prepare(self, content: Content) -> PlatformPost:
        source_body = content.body or ""
        topic = extract_discussion_topic(content)

        try:
            formatted = self._format_with_model(
                topic=topic,
                source_body=source_body,
            )
        except Exception as error:
            print(f"[REDDIT FORMATTER] LLM formatting failed: {error}")
            formatted = self._fallback_format(
                topic=topic,
                source_body=source_body,
            )

        title = normalize_title(formatted["title"], topic)
        body = normalize_body(formatted["body"], topic)

        print(
            "[REDDIT FORMATTER] source_body_chars="
            f"{len(source_body)} formatted_body_chars={len(body)} "
            f"formatted_title_chars={len(title)}"
        )

        return PlatformPost(
            title=title,
            body=body,
            platform=self.platform,
        )

    def _format_with_model(
        self,
        topic: str,
        source_body: str,
    ) -> dict[str, str]:
        prompt = f"""
You are preparing a Reddit discussion post from research content.

Topic:
{topic}

Source content:
{source_body}

Create a Reddit-native discussion post.

Requirements:
- Generate a conversational Reddit title.
- The title must sound like a real person asking a community.
- Do not use article labels such as "comparison:", "guide:", or "review:".
- Do not use marketing language.
- Do not sound like SEO or a blog headline.
- Write in first person where natural.
- Explain a realistic situation and why the poster is asking.
- Summarize observations naturally.
- Avoid excessive markdown.
- Preserve the substantive points from the source content.
- Do not intentionally truncate the discussion.
- End with an open question inviting replies.

Return only valid JSON:
{{
  "reddit_title": "...",
  "reddit_body": "..."
}}
"""

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You rewrite source research into authentic Reddit "
                        "discussion posts. You do not fabricate personal "
                        "experiences, product claims, or complaints."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.65,
        )

        raw = response.choices[0].message.content or ""
        payload = parse_json_payload(raw)

        return {
            "title": payload.get("reddit_title") or "",
            "body": payload.get("reddit_body") or "",
        }

    def _fallback_format(
        self,
        topic: str,
        source_body: str,
    ) -> dict[str, str]:
        cleaned_body = clean_article_markers(source_body)
        title = f"Has anyone compared {topic} recently?"
        body = (
            f"I've been looking into {topic} and trying to separate useful "
            "advice from generic content. A few points keep coming up:\n\n"
            f"{cleaned_body}\n\n"
            "What has everyone else's experience been? Anything important "
            "I'm overlooking?"
        )

        return {
            "title": title,
            "body": body,
        }


def parse_json_payload(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)

        if not match:
            return {}

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def extract_discussion_topic(content: Content):
    candidates = [
        content.title or "",
        content.content_type or "",
    ]

    for candidate in candidates:
        cleaned = re.sub(
            r"^(comparison|guide|review|discussion|blog_post|educational):\s*",
            "",
            candidate.strip(),
            flags=re.IGNORECASE,
        )

        if cleaned and len(cleaned) > 3:
            return cleaned

    return "this topic"


def normalize_title(title: str, topic: str):
    cleaned = clean_text(title)
    cleaned = re.sub(
        r"^(comparison|guide|review|discussion|blog_post|educational):\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    if not cleaned:
        return f"Has anyone compared {topic} recently?"

    if len(cleaned) > 280:
        cleaned = cleaned[:280].rsplit(" ", 1)[0].strip()

    return cleaned


def normalize_body(body: str, topic: str):
    cleaned = body.strip()

    if not cleaned:
        cleaned = (
            f"I've been looking into {topic} and trying to separate useful "
            "advice from generic content."
        )

    if not ends_with_question(cleaned):
        cleaned = (
            f"{cleaned.rstrip()}\n\n"
            "What has everyone else's experience been?"
        )

    return cleaned


def ends_with_question(body: str):
    stripped = body.rstrip()

    if stripped.endswith("?"):
        return True

    last_lines = [
        line.strip()
        for line in stripped.splitlines()[-4:]
        if line.strip()
    ]

    return any(line.endswith("?") for line in last_lines)


def clean_article_markers(body: str):
    lines = []

    for line in body.splitlines():
        stripped = line.strip()

        if not stripped:
            lines.append("")
            continue

        if stripped.lower().startswith(
            (
                "title:",
                "summary:",
                "full article:",
                "faq:",
                "references:",
                "sources:",
            )
        ):
            continue

        lines.append(stripped)

    return "\n".join(lines).strip()


def clean_text(value: str):
    return re.sub(r"\s+", " ", value or "").strip()
