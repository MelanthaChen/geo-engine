from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.schemas.query_schema import (
    QueryGenerationRequest,
    QueryGenerationResponse
)

from app.services.query_service import generate_queries

from app.core.deps import get_db


router = APIRouter()


@router.post(
    "/generate",
    response_model=QueryGenerationResponse
)
async def generate_query_list(
    request: QueryGenerationRequest,
    db: Session = Depends(get_db)
):

    queries = generate_queries(
        db=db,
        category=request.category,
        niche=request.niche,
        provider=request.provider,
    )

    return {
        "queries": queries
    }
