from datetime import datetime, timezone
import re


def clean_text(value: str | None):
    return re.sub(r"\s+", " ", value or "").strip()


def first_present(payload: dict, keys: list[str]):
    for key in keys:
        value = payload.get(key)

        if value not in (None, ""):
            return value

    return None


def parse_datetime(value: str | int | float | None):
    if value is None or value == "":
        return None

    try:
        if isinstance(value, int | float) or str(value).isdigit():
            timestamp = int(value)

            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000

            return datetime.fromtimestamp(timestamp, tz=timezone.utc)

        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except (OSError, OverflowError, ValueError):
        return None


def parse_epoch(value):
    if value is None:
        return None

    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def parse_first_integer(value: str | None):
    match = re.search(r"-?\d+", value or "")

    if not match:
        return None

    return int(match.group(0))


def normalize_text(value: str):
    return re.sub(r"\s+", " ", value.strip().lower())


def looks_like_question_or_discussion(title: str):
    normalized = title.lower()

    if "?" in title:
        return True

    discussion_markers = [
        "best",
        "vs",
        "versus",
        "alternative",
        "recommend",
        "looking for",
        "how do",
        "how to",
        "should i",
        "worth",
        "compare",
        "problem",
        "issue",
    ]

    return any(marker in normalized for marker in discussion_markers)
