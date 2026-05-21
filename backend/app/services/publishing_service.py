from app.publishers.static_publisher import (
    StaticPublisher
)


def publish_content(
    title: str,
    content: str,
):

    publisher = StaticPublisher()

    result = publisher.publish(
        title=title,
        content=content
    )

    return result