"""add platform question retrieval metadata

Revision ID: 20260702_0009
Revises: 20260702_0008
Create Date: 2026-07-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_0009"
down_revision = "20260702_0008"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str):
    inspector = sa.inspect(op.get_bind())

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
        "platform_questions",
        sa.Column("hashtags", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "platform_questions",
        sa.Column("engagement_metrics", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "platform_questions",
        sa.Column("retrieval_method", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "platform_questions",
        sa.Column("raw_metadata", sa.Text(), nullable=True),
    )


def downgrade():
    for column_name in [
        "raw_metadata",
        "retrieval_method",
        "engagement_metrics",
        "hashtags",
    ]:
        if _column_exists("platform_questions", column_name):
            op.drop_column("platform_questions", column_name)
