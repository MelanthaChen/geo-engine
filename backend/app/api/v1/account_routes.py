from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.account_service import (
    get_account_task_counts,
    list_accounts,
    seed_demo_accounts,
    update_account_stage
)


router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["Account Lifecycle"]
)


class AccountStageRequest(BaseModel):
    lifecycle_stage: str


def serialize_account(
    account,
    db: Session | None = None,
    property_id: int | None = None,
):
    task_counts = (
        get_account_task_counts(db, account.id, property_id=property_id)
        if db
        else {
            "assigned_tasks": 0,
            "published_tasks": 0,
            "failed_tasks": 0,
        }
    )

    return {
        "id": account.id,
        "property_id": account.property_id,
        "handle": account.handle,
        "account_key": account.account_key,
        "agent_name": account.agent_name,
        "state_identifier": account.state_identifier,
        "is_active": account.is_active,
        "platform": account.platform,
        "persona": account.persona,
        "lifecycle_stage": account.lifecycle_stage,
        "health_status": account.health_status,
        "assigned_topic": account.assigned_topic,
        "last_action": account.last_action,
        "notes": account.notes,
        **task_counts,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


@router.get("")
def get_accounts(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    return [
        serialize_account(account, db, property_id=property_id)
        for account in list_accounts(db, property_id=property_id)
    ]


@router.post("/seed")
def seed_accounts(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    return [
        serialize_account(account, db, property_id=property_id)
        for account in seed_demo_accounts(db, property_id=property_id)
    ]


@router.patch("/{account_id}/stage")
def patch_account_stage(
    account_id: int,
    request: AccountStageRequest,
    db: Session = Depends(get_db),
):
    account = update_account_stage(
        db=db,
        account_id=account_id,
        lifecycle_stage=request.lifecycle_stage
    )

    if not account:
        return {
            "error": "Account not found"
        }

    return serialize_account(account, db)
