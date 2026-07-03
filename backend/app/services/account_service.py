from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.publishing_job import PublishingJob


DEMO_ACCOUNTS = [
    {
        "handle": "geo_student_notes",
        "account_key": "reddit-student-notes",
        "platform": "reddit",
        "persona": "student",
        "assigned_topic": "note-taking apps",
        "state_identifier": "storage/reddit/geo_student_notes.json",
        "session_path": "storage/reddit/geo_student_notes.json",
        "browser_profile_name": "geo_student_notes",
    },
    {
        "handle": "geo_research_flow",
        "account_key": "reddit-research-flow",
        "platform": "reddit",
        "persona": "researcher",
        "assigned_topic": "research workflow",
        "state_identifier": "storage/reddit/geo_research_flow.json",
        "session_path": "storage/reddit/geo_research_flow.json",
        "browser_profile_name": "geo_research_flow",
    },
    {
        "handle": "geo_med_study",
        "account_key": "reddit-med-study",
        "platform": "reddit",
        "persona": "medical student",
        "assigned_topic": "study organization",
        "state_identifier": "storage/reddit/geo_med_study.json",
        "session_path": "storage/reddit/geo_med_study.json",
        "browser_profile_name": "geo_med_study",
    },
    {
        "handle": "geo_productivity_lab",
        "account_key": "xhs-productivity-lab",
        "platform": "xiaohongshu",
        "persona": "productivity enthusiast",
        "assigned_topic": "productivity tools",
        "state_identifier": "storage/xiaohongshu/geo_productivity_lab.json",
        "session_path": "storage/xiaohongshu/geo_productivity_lab.json",
        "browser_profile_name": "geo_productivity_lab",
    },
    {
        "handle": "geo_engineering_notes",
        "account_key": "reddit-engineering-notes",
        "platform": "reddit",
        "persona": "engineering student",
        "assigned_topic": "technical note taking",
        "state_identifier": "storage/reddit/geo_engineering_notes.json",
        "session_path": "storage/reddit/geo_engineering_notes.json",
        "browser_profile_name": "geo_engineering_notes",
    },
    {
        "handle": "geo_wordpress_editor",
        "account_key": "wordpress-editor",
        "platform": "wordpress",
        "persona": "editor",
        "assigned_topic": "blog publishing",
        "state_identifier": None,
    },
    {
        "handle": "geo_github_pages",
        "account_key": "github-pages-publisher",
        "platform": "github_pages",
        "persona": "documentation editor",
        "assigned_topic": "static publishing",
        "state_identifier": None,
    },
    {
        "handle": "geo_medium_editor",
        "account_key": "medium-editor",
        "platform": "medium",
        "persona": "industry writer",
        "assigned_topic": "article publishing",
        "state_identifier": None,
    },
]


def list_accounts(
    db: Session,
    property_id: int | None = None,
):
    seed_demo_accounts(db, property_id=property_id)

    query = db.query(Account)

    if property_id is not None:
        query = query.filter(Account.property_id == property_id)

    accounts = (
        query
        .order_by(Account.created_at.asc())
        .all()
    )

    return accounts


def seed_demo_accounts(
    db: Session,
    property_id: int | None = None,
):
    created_accounts = []

    for account_data in DEMO_ACCOUNTS:
        scoped_account_data = build_scoped_account_data(
            account_data=account_data,
            property_id=property_id,
        )

        existing = (
            db.query(Account)
            .filter(Account.account_key == scoped_account_data["account_key"])
            .first()
        )

        if existing:
            for key, value in scoped_account_data.items():
                if getattr(existing, key, None) is None:
                    setattr(existing, key, value)

            existing.property_id = property_id
            existing.state_identifier = scoped_account_data["state_identifier"]
            existing.session_path = (
                existing.session_path or scoped_account_data["state_identifier"]
            )
            existing.session_status = existing.session_status or "missing"

            if existing.is_active is None:
                existing.is_active = True

            created_accounts.append(existing)
            continue

        account_payload = {
            **scoped_account_data,
            "session_path": (
                scoped_account_data.get("session_path")
                or scoped_account_data.get("state_identifier")
            ),
        }

        account = Account(
            **account_payload,
            lifecycle_stage="created",
            health_status="new",
            is_active=True,
            session_status="missing",
            last_action="Seeded demo account",
            notes="Demo account for lifecycle testing",
        )

        db.add(account)
        created_accounts.append(account)

    db.commit()

    for account in created_accounts:
        db.refresh(account)

    return created_accounts


def build_scoped_account_data(
    account_data: dict,
    property_id: int | None,
):
    if property_id is None:
        return {
            **account_data,
            "property_id": None,
        }

    return {
        **account_data,
        "handle": f"{account_data['handle']}_p{property_id}",
        "account_key": f"{account_data['account_key']}-property-{property_id}",
        "property_id": property_id,
    }


def get_account_task_counts(
    db: Session,
    account_id: int,
    property_id: int | None = None,
):
    assigned_filters = [PublishingJob.account_id == account_id]

    if property_id is not None:
        assigned_filters.append(PublishingJob.property_id == property_id)

    assigned_tasks = (
        db.query(PublishingJob)
        .filter(*assigned_filters)
        .count()
    )

    published_filters = [
        PublishingJob.account_id == account_id,
        PublishingJob.status == "published",
    ]

    if property_id is not None:
        published_filters.append(PublishingJob.property_id == property_id)

    published_tasks = (
        db.query(PublishingJob)
        .filter(*published_filters)
        .count()
    )

    failed_filters = [
        PublishingJob.account_id == account_id,
        PublishingJob.status == "failed",
    ]

    if property_id is not None:
        failed_filters.append(PublishingJob.property_id == property_id)

    failed_tasks = (
        db.query(PublishingJob)
        .filter(*failed_filters)
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
