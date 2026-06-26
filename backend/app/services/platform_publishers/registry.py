from app.services.platform_publishers.reddit import RedditPublisher
from app.services.platform_publishers.unsupported import UnsupportedPublisher


PUBLISHER_REGISTRY = {
    "reddit": RedditPublisher,
}


def get_platform_publisher(platform: str | None):
    normalized_platform = (platform or "").strip().lower()
    publisher_class = PUBLISHER_REGISTRY.get(normalized_platform)

    if not publisher_class:
        return UnsupportedPublisher(normalized_platform or "unknown")

    return publisher_class()
