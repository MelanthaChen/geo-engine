import time
import requests

from app.core.config import settings
from app.services.platform_publishers import (
    PublishRequest,
    get_platform_publisher,
)

print("[TRACE] entering publisher_agent")

BACKEND_URL = (
    "https://geo-engine.onrender.com"
)


while True:

    try:
        if settings.ACCOUNT_ID:
            pending_url = (
                f"{BACKEND_URL}/api/v1/publishing/pending/"
                f"{settings.ACCOUNT_ID}"
            )

            params = (
                {"agent_name": settings.AGENT_NAME}
                if settings.AGENT_NAME
                else None
            )
        else:
            pending_url = f"{BACKEND_URL}/api/v1/publishing/pending"
            params = None

        response = requests.get(
            pending_url,
            params=params
        )

        data = response.json()

        task = data["task"]

        if task:

            print(
                f"Publishing task {task['publish_task_id']} "
                f"for account {task['account_id']}"
            )
            print(
                "[PUBLISH TRACE] worker_loaded_title_chars="
                f"{len(task['title'])} worker_loaded_body_chars="
                f"{len(task['body'])} source_body_chars="
                f"{task.get('source_body_chars')} formatted_body_chars="
                f"{task.get('formatted_body_chars')}"
            )

            try:
                publisher = get_platform_publisher(task["platform"])
                result = publisher.publish(
                    PublishRequest(
                        target=task["subreddit"],
                        title=task["title"],
                        body=task["body"],
                    )
                )

                requests.post(
                    f"{BACKEND_URL}/api/v1/publishing/complete",
                    json={
                        "content_id": task["content_id"],
                        "publish_task_id": task["publish_task_id"],
                        "url": result["url"],
                        "status": result.get("status", "review_ready"),
                        "preview_title": result.get("preview_title"),
                        "preview_subreddit": result.get("preview_subreddit"),
                        "preview_url": result.get("preview_url"),
                        "preview_screenshot": result.get("preview_screenshot"),
                        "preview_timestamp": result.get("preview_timestamp"),
                    }
                )

            except Exception:
                requests.post(
                    f"{BACKEND_URL}/api/v1/publishing/failed",
                    json={
                        "publish_task_id": task["publish_task_id"]
                    }
                )

                raise

            print("Review ready for human decision")

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
