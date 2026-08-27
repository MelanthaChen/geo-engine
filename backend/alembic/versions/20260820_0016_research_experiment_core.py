"""add reproducible research experiment core

Revision ID: 20260820_0016
Revises: 20260806_0015
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0016"
down_revision = "20260806_0015"
branch_labels = None
depends_on = None


def upgrade():
    # The initial legacy migration calls Base.metadata.create_all(), so a
    # brand-new database may already contain the current schema by the time
    # Alembic reaches this revision. Production databases at 0015 do not.
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    experiment_columns = {
        column["name"] for column in inspector.get_columns("experiments")
    }
    if {
        "experiment_prompt_versions",
        "experiment_runs",
        "experiment_evaluations",
        "experiment_metrics",
        "experiment_statistics",
        "experiment_events",
    }.issubset(tables) and "run_count" in experiment_columns:
        return

    op.create_table(
        "experiment_prompt_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_prompt_versions_checksum", "experiment_prompt_versions", ["checksum"])

    op.add_column("benchmark_datasets", sa.Column("dataset_type", sa.String(), server_default="question_set", nullable=False))
    op.add_column("benchmark_datasets", sa.Column("version", sa.String(), server_default="1", nullable=False))
    op.add_column("benchmark_datasets", sa.Column("checksum", sa.String(), nullable=True))
    op.add_column("benchmark_datasets", sa.Column("is_frozen", sa.Integer(), server_default="0", nullable=False))
    op.create_index("ix_benchmark_datasets_checksum", "benchmark_datasets", ["checksum"])

    op.add_column("experiments", sa.Column("dataset_id", sa.Integer(), nullable=True))
    op.add_column("experiments", sa.Column("dataset_version", sa.String(), server_default="1", nullable=False))
    op.add_column("experiments", sa.Column("prompt_version_id", sa.Integer(), nullable=True))
    op.add_column("experiments", sa.Column("generation_params_json", sa.Text(), nullable=True))
    op.add_column("experiments", sa.Column("run_count", sa.Integer(), server_default="0", nullable=False))
    op.create_index("ix_experiments_dataset_id", "experiments", ["dataset_id"])
    op.create_index("ix_experiments_prompt_version_id", "experiments", ["prompt_version_id"])
    op.create_foreign_key("fk_experiments_dataset", "experiments", "benchmark_datasets", ["dataset_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_experiments_prompt_version", "experiments", "experiment_prompt_versions", ["prompt_version_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("experiment_query_id", sa.Integer(), nullable=True),
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("sample_index", sa.Integer(), nullable=False),
        sa.Column("seed_value", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("raw_prompt", sa.Text(), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("generation_params_json", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("token_cost", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experiment_query_id"], ["experiment_queries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["experiment_prompt_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("experiment_id", "experiment_query_id", "prompt_version_id", "strategy", "provider", "status"):
        op.create_index(f"ix_experiment_runs_{column}", "experiment_runs", [column])

    op.add_column("experiment_strategy_results", sa.Column("run_id", sa.Integer(), nullable=True))
    op.create_index("ix_experiment_strategy_results_run_id", "experiment_strategy_results", ["run_id"])
    op.create_foreign_key("fk_strategy_result_run", "experiment_strategy_results", "experiment_runs", ["run_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "experiment_evaluations",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("evaluator", sa.String(), nullable=False), sa.Column("evaluator_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False), sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["experiment_runs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_evaluations_run_id", "experiment_evaluations", ["run_id"])

    op.create_table(
        "experiment_metrics",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False), sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True), sa.Column("unit", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True), sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["experiment_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_id"], ["experiment_evaluations.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    for column in ("run_id", "evaluation_id", "name"):
        op.create_index(f"ix_experiment_metrics_{column}", "experiment_metrics", [column])

    op.create_table(
        "experiment_statistics",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False), sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False), sa.Column("mean", sa.Float(), nullable=True),
        sa.Column("median", sa.Float(), nullable=True), sa.Column("variance", sa.Float(), nullable=True),
        sa.Column("stddev", sa.Float(), nullable=True), sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True), sa.Column("confidence_level", sa.Float(), nullable=False),
        sa.Column("confidence_low", sa.Float(), nullable=True), sa.Column("confidence_high", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    for column in ("experiment_id", "strategy", "metric_name"):
        op.create_index(f"ix_experiment_statistics_{column}", "experiment_statistics", [column])

    op.create_table(
        "experiment_events",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True), sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_events_experiment_id", "experiment_events", ["experiment_id"])
    op.create_index("ix_experiment_events_event_type", "experiment_events", ["event_type"])


def downgrade():
    op.drop_table("experiment_events")
    op.drop_table("experiment_statistics")
    op.drop_table("experiment_metrics")
    op.drop_table("experiment_evaluations")
    op.drop_constraint("fk_strategy_result_run", "experiment_strategy_results", type_="foreignkey")
    op.drop_index("ix_experiment_strategy_results_run_id", table_name="experiment_strategy_results")
    op.drop_column("experiment_strategy_results", "run_id")
    op.drop_table("experiment_runs")
    op.drop_constraint("fk_experiments_prompt_version", "experiments", type_="foreignkey")
    op.drop_constraint("fk_experiments_dataset", "experiments", type_="foreignkey")
    for column in ("run_count", "generation_params_json", "prompt_version_id", "dataset_version", "dataset_id"):
        op.drop_column("experiments", column)
    op.drop_index("ix_benchmark_datasets_checksum", table_name="benchmark_datasets")
    for column in ("is_frozen", "checksum", "version", "dataset_type"):
        op.drop_column("benchmark_datasets", column)
    op.drop_table("experiment_prompt_versions")
