"""add immutable Teacher Pipeline datasets

Revision ID: 20260923_0019
Revises: 20260903_0018
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260923_0019"
down_revision = "20260903_0018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "teacher_training_samples",
        sa.Column("sample_id", sa.String(length=36), nullable=False),
        sa.Column("website_id", sa.Integer(), nullable=True),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("experiment_run_id", sa.Integer(), nullable=False),
        sa.Column("baseline_run_id", sa.Integer(), nullable=False),
        sa.Column("experiment_query_id", sa.Integer(), nullable=False),
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("audit_version", sa.String(length=100), nullable=False),
        sa.Column("feature_vector_json", sa.Text(), nullable=False),
        sa.Column("strategy", sa.String(length=100), nullable=False),
        sa.Column("teacher_provider", sa.String(length=100), nullable=False),
        sa.Column("teacher_model", sa.String(length=255), nullable=False),
        sa.Column("teacher_model_version", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("evaluation_version", sa.String(length=255), nullable=False),
        sa.Column("metric_version", sa.String(length=255), nullable=False),
        sa.Column("original_metrics_json", sa.Text(), nullable=False),
        sa.Column("optimized_metrics_json", sa.Text(), nullable=False),
        sa.Column("delta_metrics_json", sa.Text(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["website_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["experiment_run_id"], ["experiment_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["baseline_run_id"], ["experiment_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["experiment_query_id"], ["experiment_queries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["audit_id"], ["website_audits.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sample_id"),
        sa.UniqueConstraint("experiment_run_id", name="uq_teacher_sample_experiment_run"),
        sa.UniqueConstraint("provenance_hash"),
    )
    for column in ("website_id", "experiment_id", "experiment_run_id", "baseline_run_id", "experiment_query_id", "audit_id", "strategy", "teacher_model", "provenance_hash", "dataset_version"):
        op.create_index(f"ix_teacher_training_samples_{column}", "teacher_training_samples", [column])

    op.create_table(
        "teacher_dataset_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("creation_time", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("teacher_model", sa.String(length=255), nullable=False),
        sa.Column("metric_version", sa.String(length=255), nullable=False),
        sa.Column("experiment_count", sa.Integer(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_version"),
        sa.UniqueConstraint("manifest_hash"),
    )
    op.create_index("ix_teacher_dataset_versions_dataset_version", "teacher_dataset_versions", ["dataset_version"])

    op.create_table(
        "teacher_dataset_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_version_id", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["teacher_dataset_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sample_id"], ["teacher_training_samples.sample_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_version_id", "sample_id", name="uq_teacher_dataset_member"),
    )
    op.create_index("ix_teacher_dataset_members_dataset_version_id", "teacher_dataset_members", ["dataset_version_id"])
    op.create_index("ix_teacher_dataset_members_sample_id", "teacher_dataset_members", ["sample_id"])


def downgrade():
    op.drop_table("teacher_dataset_members")
    op.drop_table("teacher_dataset_versions")
    op.drop_table("teacher_training_samples")
