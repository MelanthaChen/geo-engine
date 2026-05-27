from sqlalchemy.orm import Session

from app.models.content import Content

from app.services.reddit_publisher import (
    publish_to_reddit
)


def publish_content(
    db: Session,
    content_id: int,
):

    content = (
        db.query(Content)
        .filter(Content.id == content_id)
        .first()
    )

    if not content:

        return {
            "error": "Content not found"
        }

    result = publish_to_reddit(
        username="GeoE26527",
        password="j3R90gV*H5mY",
        subreddit="test",
        title=content.title,
        body=content.body
    )

    content.publish_status = "published"

    content.published_url = result["url"]

    content.publish_provider = "reddit"

    db.commit()

    return {
        "status": "published",
        "url": result["url"]
    }