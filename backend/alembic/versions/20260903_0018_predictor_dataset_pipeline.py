"""add predictor dataset provenance and metrics

Revision ID: 20260903_0018
Revises: 20260903_0017
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260903_0018"
down_revision = "20260903_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("training_samples", "answer", new_column_name="generated_answer")
    op.add_column("training_samples", sa.Column("experiment_run_id", sa.Integer(), nullable=True))
    op.add_column("training_samples", sa.Column("experiment_query_id", sa.Integer(), nullable=True))
    op.add_column("training_samples", sa.Column("sample_index", sa.Integer(), nullable=True))
    op.add_column("training_samples", sa.Column("prompt", sa.Text(), nullable=True))
    op.add_column("training_samples", sa.Column("word_score", sa.Float(), nullable=True))
    op.add_column("training_samples", sa.Column("position_score", sa.Float(), nullable=True))
    op.add_column("training_samples", sa.Column("llm_provider", sa.String(), nullable=True))
    op.add_column("training_samples", sa.Column("llm_model", sa.String(), nullable=True))
    op.add_column("training_samples", sa.Column("dataset_name", sa.String(), nullable=True))
    op.add_column("training_samples", sa.Column("prompt_version", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_training_samples_experiment_run",
        "training_samples",
        "experiment_runs",
        ["experiment_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_training_samples_experiment_query",
        "training_samples",
        "experiment_queries",
        ["experiment_query_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_training_samples_experiment_run_id", "training_samples", ["experiment_run_id"], unique=True)
    op.create_index("ix_training_samples_experiment_query_id", "training_samples", ["experiment_query_id"])
    op.create_index("ix_training_samples_llm_provider", "training_samples", ["llm_provider"])
    op.create_index("ix_training_samples_llm_model", "training_samples", ["llm_model"])
    op.create_index("ix_training_samples_dataset_name", "training_samples", ["dataset_name"])
    # New samples always populate these fields. Columns stay nullable at the
    # database level so a deployment containing any legacy foundation rows is
    # preserved and reported as invalid rather than deleted during migration.


def downgrade():
    op.drop_index("ix_training_samples_dataset_name", table_name="training_samples")
    op.drop_index("ix_training_samples_llm_model", table_name="training_samples")
    op.drop_index("ix_training_samples_llm_provider", table_name="training_samples")
    op.drop_index("ix_training_samples_experiment_query_id", table_name="training_samples")
    op.drop_index("ix_training_samples_experiment_run_id", table_name="training_samples")
    op.drop_constraint("fk_training_samples_experiment_query", "training_samples", type_="foreignkey")
    op.drop_constraint("fk_training_samples_experiment_run", "training_samples", type_="foreignkey")
    for column in (
        "prompt_version",
        "dataset_name",
        "llm_model",
        "llm_provider",
        "position_score",
        "word_score",
        "prompt",
        "sample_index",
        "experiment_query_id",
        "experiment_run_id",
    ):
        op.drop_column("training_samples", column)
    op.alter_column("training_samples", "generated_answer", new_column_name="answer")
