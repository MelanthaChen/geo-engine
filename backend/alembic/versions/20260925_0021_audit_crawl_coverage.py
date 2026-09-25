"""persist website-audit crawl coverage and duplicate provenance

Revision ID: 20260925_0021
Revises: 20260923_0020
Create Date: 2026-09-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0021"
down_revision = "20260923_0020"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    audit_columns = {
        column["name"] for column in inspector.get_columns("website_audits")
    }
    page_columns = {
        column["name"] for column in inspector.get_columns("website_pages")
    }

    for column in (
        sa.Column("crawl_inventory_source", sa.String(length=30), nullable=True),
        sa.Column("crawl_limit", sa.Integer(), nullable=True),
        sa.Column("discovered_url_count", sa.Integer(), nullable=True),
        sa.Column("requested_url_count", sa.Integer(), nullable=True),
        sa.Column("successful_response_count", sa.Integer(), nullable=True),
        sa.Column("unique_content_count", sa.Integer(), nullable=True),
        sa.Column("duplicate_content_count", sa.Integer(), nullable=True),
        sa.Column("skipped_due_to_limit_count", sa.Integer(), nullable=True),
    ):
        if column.name not in audit_columns:
            op.add_column("website_audits", column)

    for column in (
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duplicate_of_url", sa.Text(), nullable=True),
    ):
        if column.name not in page_columns:
            op.add_column("website_pages", column)


def downgrade():
    for column in ("duplicate_of_url", "is_duplicate", "content_sha256"):
        op.drop_column("website_pages", column)
    for column in (
        "skipped_due_to_limit_count",
        "duplicate_content_count",
        "unique_content_count",
        "successful_response_count",
        "requested_url_count",
        "discovered_url_count",
        "crawl_limit",
        "crawl_inventory_source",
    ):
        op.drop_column("website_audits", column)
