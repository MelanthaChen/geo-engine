from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.history.delete_history_service import (
    delete_faq_set,
    delete_generated_content,
    delete_history_item,
)


router = APIRouter(
    prefix="/api/v1/history",
    tags=["History"]
)


@router.delete("/faqs/{faq_set_id}")
def delete_faq_history(
    faq_set_id: int,
    db: Session = Depends(get_db),
):
    deleted = delete_faq_set(
        db=db,
        faq_set_id=faq_set_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="FAQ history item not found"
        )

    return {
        "status": "deleted",
        "id": faq_set_id,
    }


@router.delete("/content/{generated_content_id}")
def delete_content_history(
    generated_content_id: int,
    db: Session = Depends(get_db),
):
    deleted = delete_generated_content(
        db=db,
        generated_content_id=generated_content_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Generated content history item not found"
        )

    return {
        "status": "deleted",
        "id": generated_content_id,
    }


@router.delete("/items/{item_type}/{item_id}")
def delete_any_history_item(
    item_type: str,
    item_id: int,
    db: Session = Depends(get_db),
):
    deleted = delete_history_item(
        db=db,
        item_type=item_type,
        item_id=item_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="History item not found"
        )

    return {
        "status": "deleted",
        "type": item_type,
        "id": item_id,
    }
