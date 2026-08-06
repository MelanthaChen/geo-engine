"""add citation provider comparison result metadata

Revision ID: 20260806_0015
Revises: 20260730_0014
Create Date: 2026-08-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260806_0015"
down_revision = "20260730_0014"
branch_labels = None
depends_on = None


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
    if not _table_exists("citation_test_results"):
        return

    if not _column_exists("citation_test_results", "citations_json"):
        op.add_column(
            "citation_test_results",
            sa.Column("citations_json", sa.Text(), nullable=True),
        )

    if not _column_exists("citation_test_results", "latency_ms"):
        op.add_column(
            "citation_test_results",
            sa.Column("latency_ms", sa.Integer(), nullable=True),
        )


def downgrade():
    if not _table_exists("citation_test_results"):
        return

    if _column_exists("citation_test_results", "latency_ms"):
        op.drop_column("citation_test_results", "latency_ms")

    if _column_exists("citation_test_results", "citations_json"):
        op.drop_column("citation_test_results", "citations_json")
