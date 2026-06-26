"""add formatted publishing content fields

Revision ID: 20260626_0004
Revises: 20260626_0003
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0004"
down_revision = "20260626_0003"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str):
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if table_name not in inspector.get_table_names():
        return False

    return column_name in [
        column["name"]
        for column in inspector.get_columns(table_name)
    ]


def _add_column_if_missing(table_name: str, column: sa.Column):
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    _add_column_if_missing(
        "publishing_jobs",
        sa.Column("formatted_title", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "publishing_jobs",
        sa.Column("formatted_body", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "publishing_jobs",
        sa.Column("formatter_version", sa.String(length=50), nullable=True),
    )
    _add_column_if_missing(
        "publishing_jobs",
        sa.Column("formatter_name", sa.String(length=100), nullable=True),
    )


def downgrade():
    for column_name in [
        "formatter_name",
        "formatter_version",
        "formatted_body",
        "formatted_title",
    ]:
        if _column_exists("publishing_jobs", column_name):
            op.drop_column("publishing_jobs", column_name)
