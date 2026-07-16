"""add retrieval tasks

Revision ID: 20260716_0010
Revises: 20260702_0009
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260716_0010"
down_revision = "20260702_0009"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(
        index["name"] == index_name
        for index in inspector.get_indexes(table_name)
    )


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]):
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade():
    if not _table_exists("retrieval_tasks"):
        op.create_table(
            "retrieval_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("property_id", sa.Integer(), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("content_type", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("result_count", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    for index_name, columns in (
        ("ix_retrieval_tasks_id", ["id"]),
        ("ix_retrieval_tasks_property_id", ["property_id"]),
        ("ix_retrieval_tasks_account_id", ["account_id"]),
        ("ix_retrieval_tasks_platform", ["platform"]),
        ("ix_retrieval_tasks_category", ["category"]),
        ("ix_retrieval_tasks_status", ["status"]),
    ):
        _create_index_if_missing("retrieval_tasks", index_name, columns)


def downgrade():
    if _table_exists("retrieval_tasks"):
        op.drop_table("retrieval_tasks")
