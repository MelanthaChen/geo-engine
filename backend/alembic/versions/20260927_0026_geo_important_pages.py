"""add GEO-important page selection provenance

Revision ID: 20260927_0026
Revises: 20260927_0025
"""

from alembic import op
import sqlalchemy as sa


revision = "20260927_0026"
down_revision = "20260927_0025"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("website_audits", sa.Column("candidate_page_limit", sa.Integer(), nullable=True))
    op.add_column("website_audits", sa.Column("candidate_url_count", sa.Integer(), nullable=True))
    op.add_column("website_audits", sa.Column("selected_geo_page_count", sa.Integer(), nullable=True))
    op.add_column("website_pages", sa.Column("content_family", sa.String(length=255), nullable=True))
    op.add_column("website_pages", sa.Column("selection_reasons", sa.JSON(), nullable=True))
    op.add_column("website_pages", sa.Column("geo_importance_rank", sa.Integer(), nullable=True))
    op.add_column("website_pages", sa.Column("geo_importance_score", sa.Integer(), nullable=True))
    op.add_column("website_pages", sa.Column("geo_importance_signals", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("website_pages", "geo_importance_signals")
    op.drop_column("website_pages", "geo_importance_score")
    op.drop_column("website_pages", "geo_importance_rank")
    op.drop_column("website_pages", "selection_reasons")
    op.drop_column("website_pages", "content_family")
    op.drop_column("website_audits", "selected_geo_page_count")
    op.drop_column("website_audits", "candidate_url_count")
    op.drop_column("website_audits", "candidate_page_limit")
