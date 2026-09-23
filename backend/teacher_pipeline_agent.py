"""Polling worker that processes completed experiments without changing execution."""

import time

from app.core.database import SessionLocal
from app.teacher_pipeline.teacher_pipeline import TeacherPipeline


POLL_SECONDS = 30


def run_once():
    with SessionLocal() as db:
        return TeacherPipeline(db).process_completed_experiments()


def main():
    print("[TEACHER PIPELINE] worker started")
    while True:
        try:
            result = run_once()
            if result["generated_samples"]:
                print(
                    "[TEACHER PIPELINE] dataset="
                    f"{result['dataset_version']} samples={result['generated_samples']}"
                )
        except KeyboardInterrupt:
            print("[TEACHER PIPELINE] worker stopped")
            break
        except Exception as error:
            print(f"[TEACHER PIPELINE] processing failed: {error}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
