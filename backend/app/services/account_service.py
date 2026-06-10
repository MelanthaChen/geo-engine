from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.publish_task import PublishTask


DEMO_ACCOUNTS = [
    {
        "handle": "geo_student_notes",
        "account_key": "reddit-student-notes",
        "platform": "reddit",
        "persona": "student",
        "assigned_topic": "note-taking apps",
        "state_identifier": "reddit_state.json",
    },
    {
        "handle": "geo_research_flow",
        "account_key": "reddit-research-flow",
        "platform": "reddit",
        "persona": "researcher",
        "assigned_topic": "research workflow",
        "state_identifier": "reddit_state.json",
    },
    {
        "handle": "geo_med_study",
        "account_key": "reddit-med-study",
        "platform": "reddit",
        "persona": "medical student",
        "assigned_topic": "study organization",
        "state_identifier": "reddit_state.json",
    },
    {
        "handle": "geo_productivity_lab",
        "account_key": "xhs-productivity-lab",
        "platform": "xiaohongshu",
        "persona": "productivity enthusiast",
        "assigned_topic": "productivity tools",
        "state_identifier": "xiaohongshu_state.json",
    },
    {
        "handle": "geo_engineering_notes",
        "account_key": "reddit-engineering-notes",
        "platform": "reddit",
        "persona": "engineering student",
        "assigned_topic": "technical note taking",
        "state_identifier": "reddit_state.json",
    },
]


def list_accounts(db: Session):
    seed_demo_accounts(db)

    accounts = (
        db.query(Account)
        .order_by(Account.created_at.asc())
        .all()
    )

    return accounts


def seed_demo_accounts(db: Session):
    created_accounts = []

    for account_data in DEMO_ACCOUNTS:
        existing = (
            db.query(Account)
            .filter(Account.handle == account_data["handle"])
            .first()
        )

        if existing:
            for key, value in account_data.items():
                if getattr(existing, key, None) is None:
                    setattr(existing, key, value)

            if existing.is_active is None:
                existing.is_active = True

            created_accounts.append(existing)
            continue

        account = Account(
            **account_data,
            lifecycle_stage="created",
            health_status="new",
            is_active=True,
            last_action="Seeded demo account",
            notes="Demo account for lifecycle testing",
        )

        db.add(account)
        created_accounts.append(account)

    db.commit()

    for account in created_accounts:
        db.refresh(account)

    return created_accounts


def get_account_task_counts(
    db: Session,
    account_id: int,
):
    assigned_tasks = (
        db.query(PublishTask)
        .filter(PublishTask.account_id == account_id)
        .count()
    )

    published_tasks = (
        db.query(PublishTask)
        .filter(
            PublishTask.account_id == account_id,
            PublishTask.status == "published"
        )
        .count()
    )

    failed_tasks = (
        db.query(PublishTask)
        .filter(
            PublishTask.account_id == account_id,
            PublishTask.status == "failed"
        )
        .count()
    )

    return {
        "assigned_tasks": assigned_tasks,
        "published_tasks": published_tasks,
        "failed_tasks": failed_tasks,
    }


def update_account_stage(
    db: Session,
    account_id: int,
    lifecycle_stage: str,
):
    account = (
        db.query(Account)
        .filter(Account.id == account_id)
        .first()
    )

    if not account:
        return None

    account.lifecycle_stage = lifecycle_stage
    account.last_action = f"Moved to {lifecycle_stage}"

    if lifecycle_stage in {"warming", "ready"}:
        account.health_status = "healthy"
    elif lifecycle_stage in {"paused", "blocked"}:
        account.health_status = "needs_attention"

    db.commit()
    db.refresh(account)

    return account
