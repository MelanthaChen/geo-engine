from app.services.reddit_publisher import (
    publish_to_reddit
)

publish_to_reddit(
    username="",
    password="",
    subreddit="test",
    title="GEO Engine Test",
    body="Testing Reddit automation with saved login state."
)