from sqlalchemy.orm import Session

from app.models.account import Account


DEMO_ACCOUNTS = [
    {
        "handle": "geo_student_notes",
        "platform": "reddit",
        "persona": "student",
        "assigned_topic": "note-taking apps",
    },
    {
        "handle": "geo_research_flow",
        "platform": "reddit",
        "persona": "researcher",
        "assigned_topic": "research workflow",
    },
    {
        "handle": "geo_med_study",
        "platform": "reddit",
        "persona": "medical student",
        "assigned_topic": "study organization",
    },
    {
        "handle": "geo_productivity_lab",
        "platform": "xiaohongshu",
        "persona": "productivity enthusiast",
        "assigned_topic": "productivity tools",
    },
    {
        "handle": "geo_engineering_notes",
        "platform": "reddit",
        "persona": "engineering student",
        "assigned_topic": "technical note taking",
    },
]


def list_accounts(db: Session):
    accounts = (
        db.query(Account)
        .order_by(Account.created_at.asc())
        .all()
    )

    if accounts:
        return accounts

    return seed_demo_accounts(db)


def seed_demo_accounts(db: Session):
    created_accounts = []

    for account_data in DEMO_ACCOUNTS:
        existing = (
            db.query(Account)
            .filter(Account.handle == account_data["handle"])
            .first()
        )

        if existing:
            created_accounts.append(existing)
            continue

        account = Account(
            **account_data,
            lifecycle_stage="created",
            health_status="new",
            last_action="Seeded demo account",
            notes="Demo account for lifecycle testing",
        )

        db.add(account)
        created_accounts.append(account)

    db.commit()

    for account in created_accounts:
        db.refresh(account)

    return created_accounts


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
