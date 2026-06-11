from sqlalchemy import text

from app.core.database import Base, engine

from app.models import *


print("Resetting database schema...")

with engine.begin() as connection:
    connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))

print("Creating database tables from SQLAlchemy models...")

Base.metadata.create_all(bind=engine)

print("Database reset and tables created successfully!")
