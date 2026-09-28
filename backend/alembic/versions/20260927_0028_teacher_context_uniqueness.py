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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]
        for column in inspector.get_columns("teacher_dataset_members")
    }
    if "context_fingerprint" not in columns:
        op.add_column(
            "teacher_dataset_members",
            sa.Column("context_fingerprint", sa.String(length=64), nullable=True),
        )

    inspector = sa.inspect(bind)
    indexes = {
        index["name"]
        for index in inspector.get_indexes("teacher_dataset_members")
    }
    if "ix_teacher_dataset_members_context_fingerprint" not in indexes:
        op.create_index(
            "ix_teacher_dataset_members_context_fingerprint",
            "teacher_dataset_members",
            ["context_fingerprint"],
        )

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("teacher_dataset_members")
    }
    if "uq_teacher_dataset_context" not in unique_constraints:
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
