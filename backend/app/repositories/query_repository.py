from sqlalchemy.orm import Session

from app.models.query import Query


def create_query(
    db: Session,
    category: str,
    niche: str,
    query_text: str,
    query_type: str = "general"
):

    existing_query = db.query(Query).filter(
        Query.query_text == query_text
    ).first()

    if existing_query:
        return existing_query

    query = Query(
        category=category,
        niche=niche,
        query_text=query_text,
        query_type=query_type
    )

    db.add(query)

    db.commit()

    db.refresh(query)

    return query