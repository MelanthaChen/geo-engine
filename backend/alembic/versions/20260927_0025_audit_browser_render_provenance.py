"""add audit browser-render provenance and extracted evidence

Revision ID: 20260927_0025
Revises: 20260925_0024
"""

from alembic import op
import sqlalchemy as sa


revision = "20260927_0025"
down_revision = "20260925_0024"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "website_pages",
        sa.Column("h2_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "website_pages",
        sa.Column("h3_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("website_pages", sa.Column("canonical_url", sa.Text(), nullable=True))
    op.add_column("website_pages", sa.Column("schema_types", sa.JSON(), nullable=True))
    op.add_column(
        "website_pages",
        sa.Column(
            "question_heading_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "website_pages",
        sa.Column(
            "detected_qa_pair_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "website_pages",
        sa.Column(
            "faq_like_heading_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "website_pages",
        sa.Column(
            "faq_page_schema_detected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "website_pages",
        sa.Column("extraction_method", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "website_pages",
        sa.Column("extraction_failure_reason", sa.Text(), nullable=True),
    )
    op.add_column("website_pages", sa.Column("http_word_count", sa.Integer(), nullable=True))
    op.add_column("website_pages", sa.Column("browser_word_count", sa.Integer(), nullable=True))
    op.add_column("website_pages", sa.Column("evidence_json", sa.JSON(), nullable=True))
    op.add_column(
        "website_audit_recommendations",
        sa.Column("evidence_json", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("website_audit_recommendations", "evidence_json")
    op.drop_column("website_pages", "evidence_json")
    op.drop_column("website_pages", "browser_word_count")
    op.drop_column("website_pages", "http_word_count")
    op.drop_column("website_pages", "extraction_failure_reason")
    op.drop_column("website_pages", "extraction_method")
    op.drop_column("website_pages", "faq_page_schema_detected")
    op.drop_column("website_pages", "faq_like_heading_count")
    op.drop_column("website_pages", "detected_qa_pair_count")
    op.drop_column("website_pages", "question_heading_count")
    op.drop_column("website_pages", "schema_types")
    op.drop_column("website_pages", "canonical_url")
    op.drop_column("website_pages", "h3_count")
    op.drop_column("website_pages", "h2_count")
