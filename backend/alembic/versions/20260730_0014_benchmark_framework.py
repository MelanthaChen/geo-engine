"""add benchmark framework

Revision ID: 20260730_0014
Revises: 20260730_0013
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260730_0014"
down_revision = "20260730_0013"
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
    if not _table_exists("benchmark_datasets"):
        op.create_table(
            "benchmark_datasets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("property_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_benchmark_datasets_id"),
            "benchmark_datasets",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_benchmark_datasets_name"),
            "benchmark_datasets",
            ["name"],
            unique=False,
        )
        op.create_index(
            op.f("ix_benchmark_datasets_property_id"),
            "benchmark_datasets",
            ["property_id"],
            unique=False,
        )

    if not _table_exists("benchmark_dataset_queries"):
        op.create_table(
            "benchmark_dataset_queries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("dataset_id", sa.Integer(), nullable=False),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["dataset_id"],
                ["benchmark_datasets.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_benchmark_dataset_queries_dataset_id"),
            "benchmark_dataset_queries",
            ["dataset_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_benchmark_dataset_queries_id"),
            "benchmark_dataset_queries",
            ["id"],
            unique=False,
        )

    if not _table_exists("benchmarks"):
        op.create_table(
            "benchmarks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("property_id", sa.Integer(), nullable=True),
            sa.Column("dataset_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("providers_json", sa.Text(), nullable=True),
            sa.Column("metrics_json", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.String(),
                nullable=False,
                server_default="draft",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.ForeignKeyConstraint(
                ["dataset_id"],
                ["benchmark_datasets.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_benchmarks_id"), "benchmarks", ["id"])
        op.create_index(
            op.f("ix_benchmarks_property_id"),
            "benchmarks",
            ["property_id"],
        )
        op.create_index(
            op.f("ix_benchmarks_dataset_id"),
            "benchmarks",
            ["dataset_id"],
        )
        op.create_index(op.f("ix_benchmarks_status"), "benchmarks", ["status"])

    if not _table_exists("benchmark_executions"):
        op.create_table(
            "benchmark_executions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("benchmark_id", sa.Integer(), nullable=False),
            sa.Column("property_id", sa.Integer(), nullable=True),
            sa.Column("dataset_id", sa.Integer(), nullable=True),
            sa.Column(
                "provider",
                sa.String(),
                nullable=False,
                server_default="chatgpt",
            ),
            sa.Column(
                "status",
                sa.String(),
                nullable=False,
                server_default="queued",
            ),
            sa.Column("query_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "completed_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("metrics_json", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["benchmark_id"],
                ["benchmarks.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.ForeignKeyConstraint(
                ["dataset_id"],
                ["benchmark_datasets.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_benchmark_executions_benchmark_id"),
            "benchmark_executions",
            ["benchmark_id"],
        )
        op.create_index(
            op.f("ix_benchmark_executions_dataset_id"),
            "benchmark_executions",
            ["dataset_id"],
        )
        op.create_index(
            op.f("ix_benchmark_executions_id"),
            "benchmark_executions",
            ["id"],
        )
        op.create_index(
            op.f("ix_benchmark_executions_property_id"),
            "benchmark_executions",
            ["property_id"],
        )
        op.create_index(
            op.f("ix_benchmark_executions_provider"),
            "benchmark_executions",
            ["provider"],
        )
        op.create_index(
            op.f("ix_benchmark_executions_status"),
            "benchmark_executions",
            ["status"],
        )

    if not _table_exists("benchmark_results"):
        op.create_table(
            "benchmark_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("execution_id", sa.Integer(), nullable=False),
            sa.Column("dataset_query_id", sa.Integer(), nullable=True),
            sa.Column(
                "provider",
                sa.String(),
                nullable=False,
                server_default="chatgpt",
            ),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column(
                "status",
                sa.String(),
                nullable=False,
                server_default="queued",
            ),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("mentioned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column(
                "recommendation_found",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "citation_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "visibility_score",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "response_length",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("response_snippet", sa.Text(), nullable=True),
            sa.Column("raw_response", sa.Text(), nullable=True),
            sa.Column("metrics_json", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["dataset_query_id"],
                ["benchmark_dataset_queries.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["execution_id"],
                ["benchmark_executions.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_benchmark_results_dataset_query_id"),
            "benchmark_results",
            ["dataset_query_id"],
        )
        op.create_index(
            op.f("ix_benchmark_results_execution_id"),
            "benchmark_results",
            ["execution_id"],
        )
        op.create_index(op.f("ix_benchmark_results_id"), "benchmark_results", ["id"])
        op.create_index(
            op.f("ix_benchmark_results_provider"),
            "benchmark_results",
            ["provider"],
        )
        op.create_index(
            op.f("ix_benchmark_results_status"),
            "benchmark_results",
            ["status"],
        )

    if (
        _table_exists("history_events")
        and not _column_exists("history_events", "benchmark_execution_id")
    ):
        op.add_column(
            "history_events",
            sa.Column("benchmark_execution_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f("ix_history_events_benchmark_execution_id"),
            "history_events",
            ["benchmark_execution_id"],
        )
        op.create_foreign_key(
            "fk_history_events_benchmark_execution_id",
            "history_events",
            "benchmark_executions",
            ["benchmark_execution_id"],
            ["id"],
        )


def downgrade():
    if (
        _table_exists("history_events")
        and _column_exists("history_events", "benchmark_execution_id")
    ):
        op.drop_constraint(
            "fk_history_events_benchmark_execution_id",
            "history_events",
            type_="foreignkey",
        )
        op.drop_index(
            op.f("ix_history_events_benchmark_execution_id"),
            table_name="history_events",
        )
        op.drop_column("history_events", "benchmark_execution_id")

    for table_name in (
        "benchmark_results",
        "benchmark_executions",
        "benchmarks",
        "benchmark_dataset_queries",
        "benchmark_datasets",
    ):
        if _table_exists(table_name):
            op.drop_table(table_name)
