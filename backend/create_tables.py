from sqlalchemy import text

from app.core.database import Base, engine
from app.core.database import SessionLocal

from app.models import *
from app.services.property_service import seed_default_property


print("Resetting database schema...")

with engine.begin() as connection:
    connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))

print("Creating database tables from SQLAlchemy models...")

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    seed_default_property(db)

print("Database reset and tables created successfully!")
