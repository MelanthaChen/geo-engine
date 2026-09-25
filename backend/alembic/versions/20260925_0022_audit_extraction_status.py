"""separate audit transport, HTML, and extraction status

Revision ID: 20260925_0022
Revises: 20260925_0021
Create Date: 2026-09-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0022"
down_revision = "20260925_0021"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"] for column in inspector.get_columns("website_audits")
    }
    for column in (
        sa.Column("accepted_html_response_count", sa.Integer(), nullable=True),
        sa.Column("extraction_success_count", sa.Integer(), nullable=True),
    ):
        if column.name not in columns:
            op.add_column("website_audits", column)


def downgrade():
    op.drop_column("website_audits", "extraction_success_count")
    op.drop_column("website_audits", "accepted_html_response_count")
