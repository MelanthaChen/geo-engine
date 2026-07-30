"""add LLM provider metadata fields

Revision ID: 20260730_0013
Revises: 20260724_0012
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260730_0013"
down_revision = "20260724_0012"
branch_labels = None
depends_on = None


PROVIDER_TABLES = (
    "contents",
    "faq_sets",
    "experiments",
    "experiment_campaigns",
    "citation_tests",
    "citation_results",
    "citation_test_runs",
    "citation_test_results",
)


def _table_exists(table_name: str):
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str):
    inspector = sa.inspect(op.get_bind())

    if table_name not in inspector.get_table_names():
        return False

    return column_name in {
        column["name"]
        for column in inspector.get_columns(table_name)
    }


def upgrade():
    for table_name in PROVIDER_TABLES:
        if not _table_exists(table_name) or _column_exists(table_name, "provider"):
            continue

        op.add_column(
            table_name,
            sa.Column(
                "provider",
                sa.String(),
                nullable=False,
                server_default="chatgpt",
            ),
        )


def downgrade():
    for table_name in reversed(PROVIDER_TABLES):
        if not _table_exists(table_name) or not _column_exists(table_name, "provider"):
            continue

        op.drop_column(table_name, "provider")
