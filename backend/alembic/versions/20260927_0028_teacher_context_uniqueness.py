"""enforce one formal Teacher dataset member per experimental context

Revision ID: 20260927_0028
Revises: 20260927_0027
"""

from alembic import op
import sqlalchemy as sa


revision = "20260927_0028"
down_revision = "20260927_0027"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "teacher_dataset_members",
        sa.Column("context_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_teacher_dataset_members_context_fingerprint",
        "teacher_dataset_members",
        ["context_fingerprint"],
    )
    op.create_unique_constraint(
        "uq_teacher_dataset_context",
        "teacher_dataset_members",
        ["dataset_version_id", "context_fingerprint"],
    )


def downgrade():
    op.drop_constraint(
        "uq_teacher_dataset_context",
        "teacher_dataset_members",
        type_="unique",
    )
    op.drop_index(
        "ix_teacher_dataset_members_context_fingerprint",
        table_name="teacher_dataset_members",
    )
    op.drop_column("teacher_dataset_members", "context_fingerprint")
