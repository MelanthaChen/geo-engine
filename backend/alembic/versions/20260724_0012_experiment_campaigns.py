"""add experiment campaign orchestration tables

Revision ID: 20260724_0012
Revises: 20260723_0011
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0012"
down_revision = "20260723_0011"
branch_labels = None
depends_on = None


def _table_exists(table_name: str):
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str):
    inspector = sa.inspect(op.get_bind())

    if table_name not in inspector.get_table_names():
        return False

    return column_name in [
        column["name"]
        for column in inspector.get_columns(table_name)
    ]


def _index_exists(table_name: str, index_name: str):
    inspector = sa.inspect(op.get_bind())

    if table_name not in inspector.get_table_names():
        return False

    return index_name in {
        index["name"]
        for index in inspector.get_indexes(table_name)
    }


def upgrade():
    if not _table_exists("experiment_campaigns"):
        op.create_table(
            "experiment_campaigns",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("property_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("llm_model", sa.String(), nullable=True),
            sa.Column("dataset_name", sa.String(), nullable=True),
            sa.Column("benchmark_queries_json", sa.Text(), nullable=True),
            sa.Column("strategies_json", sa.Text(), nullable=True),
            sa.Column("metrics_json", sa.Text(), nullable=True),
            sa.Column("query_count", sa.Integer(), nullable=True),
            sa.Column("seed_count", sa.Integer(), nullable=True),
            sa.Column("random_seed", sa.Integer(), nullable=True),
            sa.Column("temperature", sa.Float(), nullable=True),
            sa.Column("current_query", sa.Text(), nullable=True),
            sa.Column("current_strategy", sa.String(), nullable=True),
            sa.Column("current_seed", sa.Integer(), nullable=True),
            sa.Column("queries_completed", sa.Integer(), nullable=True),
            sa.Column("queries_remaining", sa.Integer(), nullable=True),
            sa.Column("success_count", sa.Integer(), nullable=True),
            sa.Column("failure_count", sa.Integer(), nullable=True),
            sa.Column("estimated_remaining_time", sa.String(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_experiment_campaigns_id",
            "experiment_campaigns",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_experiment_campaigns_property_id",
            "experiment_campaigns",
            ["property_id"],
            unique=False,
        )
        op.create_index(
            "ix_experiment_campaigns_status",
            "experiment_campaigns",
            ["status"],
            unique=False,
        )

    if not _column_exists("experiments", "campaign_id"):
        with op.batch_alter_table("experiments") as batch_op:
            batch_op.add_column(sa.Column("campaign_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_experiments_campaign_id_experiment_campaigns",
                "experiment_campaigns",
                ["campaign_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if not _index_exists("experiments", "ix_experiments_campaign_id"):
        op.create_index(
            "ix_experiments_campaign_id",
            "experiments",
            ["campaign_id"],
            unique=False,
        )


def downgrade():
    if _index_exists("experiments", "ix_experiments_campaign_id"):
        op.drop_index("ix_experiments_campaign_id", table_name="experiments")

    if _column_exists("experiments", "campaign_id"):
        with op.batch_alter_table("experiments") as batch_op:
            batch_op.drop_constraint(
                "fk_experiments_campaign_id_experiment_campaigns",
                type_="foreignkey",
            )
            batch_op.drop_column("campaign_id")

    if _table_exists("experiment_campaigns"):
        op.drop_table("experiment_campaigns")
