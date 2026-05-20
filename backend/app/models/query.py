from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import func

from app.core.database import Base


class Query(Base):

    __tablename__ = "queries"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    category = Column(
        String,
        nullable=False
    )

    niche = Column(
        String,
        nullable=False
    )

    query_text = Column(
        String,
        nullable=False,
        unique=True
    )

    query_type = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )