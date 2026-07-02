from app.services.platform_publishers.base import PublishRequest
from app.services.playwright_session_service import PlaywrightSessionService
from app.services.reddit_publisher import publish_to_reddit


class RedditPublisher:
    platform = "reddit"

    def publish(self, request: PublishRequest) -> dict:
        if not request.session_path:
            raise RuntimeError(
                "Reddit account session_path is missing. "
                "Create a Playwright session for this account before publishing."
            )

        session_path = PlaywrightSessionService().load_session_path(
            request.session_path
        )

        return publish_to_reddit(
            username="",
            password="",
            subreddit=request.target,
            title=request.title,
            body=request.body,
            session_path=session_path,
        )
