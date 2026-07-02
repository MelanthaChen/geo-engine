"""add account browser session metadata

Revision ID: 20260702_0008
Revises: 20260702_0007
Create Date: 2026-07-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_0008"
down_revision = "20260702_0007"
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
        "accounts",
        sa.Column("session_path", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "accounts",
        sa.Column("session_status", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "accounts",
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "accounts",
        sa.Column("last_session_refresh", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "accounts",
        sa.Column("last_session_validation", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "accounts",
        sa.Column("browser_profile_name", sa.String(), nullable=True),
    )


def downgrade():
    for column_name in [
        "browser_profile_name",
        "last_session_validation",
        "last_session_refresh",
        "last_login",
        "session_status",
        "session_path",
    ]:
        if _column_exists("accounts", column_name):
            op.drop_column("accounts", column_name)
