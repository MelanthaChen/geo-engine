from sqlalchemy import inspect, text

from app.core.database import Base, engine
from app.models import *
from app.services.property_service import seed_default_property


REQUIRED_TABLES = {
    "accounts",
    "citation_results",
    "citation_tests",
    "citation_test_results",
    "citation_test_runs",
    "contents",
    "faq_sets",
    "faqs",
    "history_events",
    "platform_questions",
    "publishing_jobs",
    "publish_tasks",
    "properties",
    "website_audit_recommendations",
    "website_audits",
    "website_pages",
}


def reset_database():
    print("Resetting database schema...")

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    print("Creating database tables from SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)

    from app.core.database import SessionLocal

    with SessionLocal() as db:
        seed_default_property(db)

    inspector = inspect(engine)
    created_tables = sorted(inspector.get_table_names(schema="public"))

    print("Tables created:")
    for table_name in created_tables:
        print(f"- {table_name}")

    missing_tables = REQUIRED_TABLES.difference(created_tables)
    if missing_tables:
        missing_table_list = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            f"Database reset failed. Missing required tables: "
            f"{missing_table_list}"
        )

    print("Required table verification passed:")
    for table_name in sorted(REQUIRED_TABLES):
        print(f"- {table_name}")

    print("Database reset completed successfully.")


if __name__ == "__main__":
    reset_database()
