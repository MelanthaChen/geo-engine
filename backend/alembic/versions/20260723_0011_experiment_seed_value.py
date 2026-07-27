"""store paper-mode seed value per experiment query

Revision ID: 20260723_0011
Revises: 20260716_0010
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0011"
down_revision = "20260716_0010"
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


def upgrade():
    if not _column_exists("experiment_queries", "seed_value"):
        with op.batch_alter_table("experiment_queries") as batch_op:
            batch_op.add_column(sa.Column("seed_value", sa.Integer(), nullable=True))

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {
        index["name"]
        for index in inspector.get_indexes("experiment_queries")
    }

    if "ix_experiment_queries_seed_value" not in index_names:
        op.create_index(
            "ix_experiment_queries_seed_value",
            "experiment_queries",
            ["seed_value"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {
        index["name"]
        for index in inspector.get_indexes("experiment_queries")
    }

    if "ix_experiment_queries_seed_value" in index_names:
        op.drop_index(
            "ix_experiment_queries_seed_value",
            table_name="experiment_queries",
        )

    if _column_exists("experiment_queries", "seed_value"):
        with op.batch_alter_table("experiment_queries") as batch_op:
            batch_op.drop_column("seed_value")
