from app.services.platform_publishers.base import PublishRequest
from app.services.reddit_publisher import publish_to_reddit


class RedditPublisher:
    platform = "reddit"

    def publish(self, request: PublishRequest) -> dict:
        return publish_to_reddit(
            username="",
            password="",
            subreddit=request.target,
            title=request.title,
            body=request.body,
        )
