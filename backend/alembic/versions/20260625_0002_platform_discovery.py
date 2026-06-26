"""platform discovery and property-scoped accounts

Revision ID: 20260625_0002
Revises: 20260625_0001
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_0002"
down_revision = "20260625_0001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str):
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if table_name not in inspector.get_table_names():
        return False

    return column_name in [
        column["name"]
        for column in inspector.get_columns(table_name)
    ]


def _index_exists(table_name: str, index_name: str):
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if table_name not in inspector.get_table_names():
        return False

    return index_name in [
        index["name"]
        for index in inspector.get_indexes(table_name)
    ]


def upgrade():
    if not _table_exists("platform_questions"):
        op.create_table(
            "platform_questions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "property_id",
                sa.Integer(),
                sa.ForeignKey("properties.id"),
                nullable=True,
            ),
            sa.Column("platform", sa.String(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("url", sa.String(), nullable=True),
            sa.Column("author", sa.String(), nullable=True),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "discovered_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("content_hash", sa.String(), nullable=False),
        )

    for index_name, columns in [
        ("ix_platform_questions_property_id", ["property_id"]),
        ("ix_platform_questions_platform", ["platform"]),
        ("ix_platform_questions_content_hash", ["content_hash"]),
    ]:
        if not _index_exists("platform_questions", index_name):
            op.create_index(
                index_name,
                "platform_questions",
                columns,
                unique=False,
            )

    if _table_exists("accounts") and not _column_exists(
        "accounts",
        "property_id",
    ):
        op.add_column(
            "accounts",
            sa.Column(
                "property_id",
                sa.Integer(),
                sa.ForeignKey("properties.id"),
                nullable=True,
            ),
        )

    if _table_exists("accounts") and not _index_exists(
        "accounts",
        "ix_accounts_property_id",
    ):
        op.create_index(
            "ix_accounts_property_id",
            "accounts",
            ["property_id"],
            unique=False,
        )


def downgrade():
    if _table_exists("accounts") and _index_exists(
        "accounts",
        "ix_accounts_property_id",
    ):
        op.drop_index("ix_accounts_property_id", table_name="accounts")

    if _table_exists("accounts") and _column_exists(
        "accounts",
        "property_id",
    ):
        op.drop_column("accounts", "property_id")

    if _table_exists("platform_questions"):
        op.drop_table("platform_questions")
