import time
import requests

from app.services.reddit_publisher import (
    publish_to_reddit
)

BACKEND_URL = (
    "https://geo-engine.onrender.com"
)


while True:

    try:

        response = requests.get(
            f"{BACKEND_URL}/api/v1/publishing/pending"
        )

        data = response.json()

        task = data["task"]

        if task:

            print(
                f"Publishing content {task['id']}"
            )

            result = publish_to_reddit(
                username="",
                password="",
                subreddit=task["subreddit"],
                title=task["title"],
                body=task["body"]
            )

            requests.post(
                f"{BACKEND_URL}/api/v1/publishing/complete",
                json={
                    "content_id": task["id"],
                    "url": result["url"]
                }
            )

            print(
                "Published successfully"
            )

        else:

            print(
                "No pending tasks"
            )

    except Exception as e:

        print(
            "Agent Error:",
            e
        )

    time.sleep(10)