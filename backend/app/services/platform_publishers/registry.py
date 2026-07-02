from app.services.platform_publishers.reddit import RedditPublisher
from app.services.platform_publishers.unsupported import UnsupportedPublisher
from app.services.platform_publishers.xiaohongshu import XiaohongshuPublisher


PUBLISHER_REGISTRY = {
    "reddit": RedditPublisher,
    "xiaohongshu": XiaohongshuPublisher,
}


def get_platform_publisher(platform: str | None):
    normalized_platform = (platform or "").strip().lower()
    publisher_class = PUBLISHER_REGISTRY.get(normalized_platform)

    if not publisher_class:
        return UnsupportedPublisher(normalized_platform or "unknown")

    return publisher_class()
