import importlib.util
from pathlib import Path

from app.models.website_audit import WebsiteAudit
from app.models.website_audit_recommendation import WebsiteAuditRecommendation
from app.models.website_page import WebsitePage


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260927_0027_repair_evidence_columns.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("repair_0027", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_repair_manifest_matches_current_audit_models():
    migration = load_migration()
    model_columns = {
        "website_pages": set(WebsitePage.__table__.columns.keys()),
        "website_audit_recommendations": set(
            WebsiteAuditRecommendation.__table__.columns.keys()
        ),
        "website_audits": set(WebsiteAudit.__table__.columns.keys()),
    }

    for table_name, columns in migration.EXPECTED_COLUMNS.items():
        expected_names = {column.name for column in columns}
        assert expected_names <= model_columns[table_name]


def test_repair_adds_only_missing_columns_and_is_idempotent(monkeypatch):
    migration = load_migration()
    existing = {
        table_name: {column.name for column in columns}
        for table_name, columns in migration.EXPECTED_COLUMNS.items()
    }
    existing["website_pages"].remove("evidence_json")
    existing["website_audit_recommendations"].remove("evidence_json")
    added = []

    monkeypatch.setattr(
        migration,
        "_existing_column_names",
        lambda table_name: set(existing[table_name]),
    )

    def add_column(table_name, column):
        added.append((table_name, column.name))
        existing[table_name].add(column.name)

    monkeypatch.setattr(migration.op, "add_column", add_column)

    migration.upgrade()
    migration.upgrade()

    assert added == [
        ("website_pages", "evidence_json"),
        ("website_audit_recommendations", "evidence_json"),
    ]
