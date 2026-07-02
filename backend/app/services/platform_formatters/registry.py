from app.services.platform_formatters.default_formatter import DefaultFormatter
from app.services.platform_formatters.reddit_formatter import RedditFormatter
from app.services.platform_formatters.xiaohongshu_formatter import (
    XiaohongshuFormatter,
)


FORMATTER_REGISTRY = {
    "reddit": RedditFormatter,
    "xiaohongshu": XiaohongshuFormatter,
}


def get_platform_formatter(platform: str | None):
    normalized_platform = (platform or "").strip().lower()
    formatter_class = FORMATTER_REGISTRY.get(
        normalized_platform,
        DefaultFormatter,
    )

    return formatter_class()
