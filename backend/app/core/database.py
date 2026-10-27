from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    # Render Free services may sleep while PostgreSQL closes idle SSL
    # connections. Validate pooled connections before handing them to a
    # request so the profile-import route reconnects instead of failing on a
    # stale socket.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
