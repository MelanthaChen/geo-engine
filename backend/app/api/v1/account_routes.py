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
from app.models.account import Account
from app.services.playwright_session_service import PlaywrightSessionService


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
        "session_path": account.session_path,
        "session_status": account.session_status,
        "last_login": account.last_login,
        "last_session_refresh": account.last_session_refresh,
        "last_session_validation": account.last_session_validation,
        "browser_profile_name": account.browser_profile_name,
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


@router.post("/{account_id}/session")
def create_account_session(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        return {
            "error": "Account not found"
        }

    session_path = PlaywrightSessionService(db=db).create_session(account)

    return {
        "status": "session_saved",
        "account": serialize_account(account, db),
        "session_path": str(session_path),
    }


@router.post("/{account_id}/session/validate")
def validate_account_session(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        return {
            "error": "Account not found"
        }

    is_valid = PlaywrightSessionService(db=db).validate_session(account)

    return {
        "status": "valid" if is_valid else "missing",
        "account": serialize_account(account, db),
    }


@router.delete("/{account_id}/session")
def delete_account_session(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        return {
            "error": "Account not found"
        }

    PlaywrightSessionService(db=db).delete_session(account)

    return {
        "status": "session_deleted",
        "account": serialize_account(account, db),
    }
