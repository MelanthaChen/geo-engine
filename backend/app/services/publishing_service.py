from sqlalchemy.orm import Session

from app.publishers.static_publisher import (
    StaticPublisher
)

from app.repositories.content_repository import (
    get_content_by_id,
    update_content_publish_info
)


def publish_content(
    db: Session,
    content_id: int,
):

    content = get_content_by_id(
        db=db,
        content_id=content_id
    )

    if not content:

        return {
            "error": "Content not found"
        }

    publisher = StaticPublisher()

    publish_result = publisher.publish(
        title=content.title,
        content=content.body
    )

    updated_content = (
        update_content_publish_info(
            db=db,
            content=content,
            publish_result=publish_result
        )
    )

    return {
        "status": "published",
        "content_id": updated_content.id,
        "published_url":
            updated_content.published_url,
        "provider":
            updated_content.publish_provider
    }