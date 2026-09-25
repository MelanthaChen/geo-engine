"""add evidence-backed audit opportunity fields

Revision ID: 20260925_0024
Revises: 20260925_0023
"""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0024"
down_revision = "20260925_0023"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("website_audit_recommendations", sa.Column("observed_evidence", sa.Text(), nullable=True))
    op.add_column("website_audit_recommendations", sa.Column("affected_page_count", sa.Integer(), nullable=True))
    op.add_column("website_audit_recommendations", sa.Column("evaluated_page_count", sa.Integer(), nullable=True))
    op.add_column("website_audit_recommendations", sa.Column("why_it_matters", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("website_audit_recommendations", "why_it_matters")
    op.drop_column("website_audit_recommendations", "evaluated_page_count")
    op.drop_column("website_audit_recommendations", "affected_page_count")
    op.drop_column("website_audit_recommendations", "observed_evidence")
