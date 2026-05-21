import os

from datetime import datetime

from app.publishers.base_publisher import BasePublisher


class StaticPublisher(BasePublisher):

    def publish(
        self,
        title: str,
        content: str,
    ):

        os.makedirs(
            "published_pages",
            exist_ok=True
        )

        filename = (
            title.lower()
            .replace(" ", "-")
        )

        filepath = (
            f"published_pages/{filename}.html"
        )

        html = f"""
        <html>

        <head>
            <title>{title}</title>
        </head>

        <body>

            <h1>{title}</h1>

            <div>
                {content}
            </div>

        </body>

        </html>
        """

        with open(
            filepath,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(html)

        return {
            "status": "published",
            "provider": "static",
            "url": filepath,
            "published_at":
                datetime.utcnow()
                .isoformat()
        }

    def update(
        self,
        content_id: int,
        title: str,
        content: str,
    ):

        return {
            "status": "updated"
        }

    def delete(
        self,
        content_id: int,
    ):

        return {
            "status": "deleted"
        }