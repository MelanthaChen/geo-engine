"""add paper reproduction experiment tables

Revision ID: 20260702_0007
Revises: 20260628_0006
Create Date: 2026-07-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_0007"
down_revision = "20260628_0006"
branch_labels = None
depends_on = None


EXPERIMENT_COLUMNS = {
    "description": sa.Column("description", sa.Text(), nullable=True),
    "llm_model": sa.Column("llm_model", sa.String(), nullable=True),
    "dataset_name": sa.Column("dataset_name", sa.String(), nullable=True),
    "strategies_json": sa.Column("strategies_json", sa.Text(), nullable=True),
    "metrics_json": sa.Column("metrics_json", sa.Text(), nullable=True),
    "number_of_queries": sa.Column("number_of_queries", sa.Integer(), nullable=True),
    "random_seed": sa.Column("random_seed", sa.Integer(), nullable=True),
    "temperature": sa.Column("temperature", sa.Float(), nullable=True),
    "current_query": sa.Column("current_query", sa.Text(), nullable=True),
    "current_strategy": sa.Column("current_strategy", sa.String(), nullable=True),
    "completed_queries": sa.Column("completed_queries", sa.Integer(), nullable=True),
    "total_queries": sa.Column("total_queries", sa.Integer(), nullable=True),
    "estimated_remaining_time": sa.Column(
        "estimated_remaining_time",
        sa.String(),
        nullable=True,
    ),
    "error_message": sa.Column("error_message", sa.Text(), nullable=True),
    "visibility_score": sa.Column("visibility_score", sa.Float(), nullable=True),
    "citation_count": sa.Column("citation_count", sa.Integer(), nullable=True),
    "pawc": sa.Column("pawc", sa.Float(), nullable=True),
    "updated_at": sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=True,
    ),
    "completed_at": sa.Column(
        "completed_at",
        sa.DateTime(timezone=True),
        nullable=True,
    ),
}


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


def upgrade():
    if not _table_exists("experiments"):
        op.create_table(
            "experiments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("property_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("target_platform", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_experiments_id", "experiments", ["id"], unique=False)
        op.create_index(
            "ix_experiments_property_id",
            "experiments",
            ["property_id"],
            unique=False,
        )

    with op.batch_alter_table("experiments") as batch_op:
        for column_name, column in EXPERIMENT_COLUMNS.items():
            if not _column_exists("experiments", column_name):
                batch_op.add_column(column)

    if not _table_exists("experiment_queries"):
        op.create_table(
            "experiment_queries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("experiment_id", sa.Integer(), nullable=False),
            sa.Column("query", sa.Text(), nullable=False),
            sa.Column("selected_document_rank", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["experiment_id"],
                ["experiments.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_experiment_queries_experiment_id",
            "experiment_queries",
            ["experiment_id"],
            unique=False,
        )
        op.create_index(
            "ix_experiment_queries_id",
            "experiment_queries",
            ["id"],
            unique=False,
        )

    if not _table_exists("experiment_documents"):
        op.create_table(
            "experiment_documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("experiment_query_id", sa.Integer(), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("plain_text", sa.Text(), nullable=False),
            sa.Column("is_selected", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["experiment_query_id"],
                ["experiment_queries.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_experiment_documents_experiment_query_id",
            "experiment_documents",
            ["experiment_query_id"],
            unique=False,
        )
        op.create_index(
            "ix_experiment_documents_id",
            "experiment_documents",
            ["id"],
            unique=False,
        )

    if not _table_exists("experiment_strategy_results"):
        op.create_table(
            "experiment_strategy_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("experiment_query_id", sa.Integer(), nullable=False),
            sa.Column("strategy", sa.String(), nullable=False),
            sa.Column("modified_document_text", sa.Text(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("answer", sa.Text(), nullable=False),
            sa.Column("word_count", sa.Integer(), nullable=True),
            sa.Column("position", sa.Integer(), nullable=True),
            sa.Column("pawc", sa.Float(), nullable=True),
            sa.Column("citation_count", sa.Integer(), nullable=True),
            sa.Column("visibility_score", sa.Float(), nullable=True),
            sa.Column("is_winner", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["experiment_query_id"],
                ["experiment_queries.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_experiment_strategy_results_experiment_query_id",
            "experiment_strategy_results",
            ["experiment_query_id"],
            unique=False,
        )
        op.create_index(
            "ix_experiment_strategy_results_id",
            "experiment_strategy_results",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_experiment_strategy_results_strategy",
            "experiment_strategy_results",
            ["strategy"],
            unique=False,
        )


def downgrade():
    op.drop_table("experiment_strategy_results")
    op.drop_table("experiment_documents")
    op.drop_table("experiment_queries")

    with op.batch_alter_table("experiments") as batch_op:
        for column_name in reversed(list(EXPERIMENT_COLUMNS.keys())):
            if _column_exists("experiments", column_name):
                batch_op.drop_column(column_name)
