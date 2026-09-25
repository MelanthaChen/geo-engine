"""add audit discovery provenance

Revision ID: 20260925_0023
Revises: 20260925_0022
"""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0023"
down_revision = "20260925_0022"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("website_audits", sa.Column("robots_txt_detected", sa.Boolean(), nullable=True))
    op.add_column("website_audits", sa.Column("sitemap_url_count", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("website_audits", "sitemap_url_count")
    op.drop_column("website_audits", "robots_txt_detected")
