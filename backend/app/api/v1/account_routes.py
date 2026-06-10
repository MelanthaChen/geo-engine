from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.account_service import (
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


def serialize_account(account):
    return {
        "id": account.id,
        "handle": account.handle,
        "platform": account.platform,
        "persona": account.persona,
        "lifecycle_stage": account.lifecycle_stage,
        "health_status": account.health_status,
        "assigned_topic": account.assigned_topic,
        "last_action": account.last_action,
        "notes": account.notes,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


@router.get("")
def get_accounts(
    db: Session = Depends(get_db),
):
    return [
        serialize_account(account)
        for account in list_accounts(db)
    ]


@router.post("/seed")
def seed_accounts(
    db: Session = Depends(get_db),
):
    return [
        serialize_account(account)
        for account in seed_demo_accounts(db)
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

    return serialize_account(account)
