import time
from dataclasses import asdict
from datetime import datetime

import requests

from app.core.config import settings
from app.services.platform_retrievers.xiaohongshu import XiaohongshuRetriever


BACKEND_URL = settings.BACKEND_URL.rstrip("/")
POLL_SECONDS = 5


def serialize_question(question):
    payload = asdict(question)
    created_at = payload.get("created_at")

    if isinstance(created_at, datetime):
        payload["created_at"] = created_at.isoformat()

    return payload


def fail_task(task_id: int, message: str):
    requests.post(
        f"{BACKEND_URL}/api/v1/content/retrieval-tasks/{task_id}/failed",
        json={"error_message": message},
        timeout=30,
    )


def run_task(task: dict):
    task_id = task["id"]
    category = task["category"]
    property_id = task.get("property_id")

    print(
        "[RETRIEVER] claimed task "
        f"id={task_id} platform=xiaohongshu category={category!r} "
        f"property_id={property_id}"
    )

    retriever = XiaohongshuRetriever()
    questions = retriever.search(
        query=category,
        limit=settings.XIAOHONGSHU_RETRIEVAL_LIMIT,
        property_id=property_id,
    )

    print(
        "[RETRIEVER] xiaohongshu retrieval completed "
        f"task_id={task_id} retrieved={len(questions)}"
    )

    response = requests.post(
        f"{BACKEND_URL}/api/v1/content/retrieval-tasks/{task_id}/complete",
        json={
            "questions": [
                serialize_question(question)
                for question in questions
            ],
        },
        timeout=60,
    )
    response.raise_for_status()

    completed = response.json()["task"]
    print(
        "[RETRIEVER] task completed "
        f"id={task_id} saved={completed.get('result_count')}"
    )


def main():
    print("[RETRIEVER] Xiaohongshu retriever_agent started")
    print(f"[RETRIEVER] backend_url={BACKEND_URL}")

    while True:
        try:
            response = requests.get(
                f"{BACKEND_URL}/api/v1/content/retrieval-tasks/pending",
                params={"platform": "xiaohongshu"},
                timeout=30,
            )
            response.raise_for_status()
            task = response.json().get("task")

            if not task:
                print("[RETRIEVER] no pending Xiaohongshu retrieval tasks")
                time.sleep(POLL_SECONDS)
                continue

            try:
                run_task(task)
            except KeyboardInterrupt:
                raise
            except Exception as error:
                print(
                    "[RETRIEVER] task failed "
                    f"id={task.get('id')} error={error}"
                )
                fail_task(task["id"], str(error))

        except KeyboardInterrupt:
            print("[RETRIEVER] stopped")
            break
        except Exception as error:
            print(f"[RETRIEVER] agent error: {error}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
