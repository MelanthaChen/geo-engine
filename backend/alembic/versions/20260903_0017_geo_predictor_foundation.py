"""add GEO Predictor training sample foundation

Revision ID: 20260903_0017
Revises: 20260820_0016
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260903_0017"
down_revision = "20260820_0016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "training_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("original_document", sa.Text(), nullable=False),
        sa.Column("modified_document", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("visibility_score", sa.Float(), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=True),
        sa.Column("subjective_score", sa.Float(), nullable=True),
        sa.Column("pawc", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_samples_id", "training_samples", ["id"])
    op.create_index(
        "ix_training_samples_experiment_id",
        "training_samples",
        ["experiment_id"],
    )
    op.create_index("ix_training_samples_strategy", "training_samples", ["strategy"])


def downgrade():
    op.drop_index("ix_training_samples_strategy", table_name="training_samples")
    op.drop_index("ix_training_samples_experiment_id", table_name="training_samples")
    op.drop_index("ix_training_samples_id", table_name="training_samples")
    op.drop_table("training_samples")
