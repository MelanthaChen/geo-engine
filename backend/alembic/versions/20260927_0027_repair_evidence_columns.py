"""repair Website Audit evidence and selection columns

Revision ID: 20260927_0027
Revises: 20260927_0026

This is a forward-only reconciliation for databases that applied an earlier
version of revision 0025 before evidence_json was appended to that file.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260927_0027"
down_revision = "20260927_0026"
branch_labels = None
depends_on = None


EXPECTED_COLUMNS = {
    "website_pages": (
        sa.Column("h2_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("h3_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("schema_types", sa.JSON(), nullable=True),
        sa.Column("question_heading_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detected_qa_pair_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("faq_like_heading_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("faq_page_schema_detected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("extraction_method", sa.String(length=20), nullable=True),
        sa.Column("extraction_failure_reason", sa.Text(), nullable=True),
        sa.Column("http_word_count", sa.Integer(), nullable=True),
        sa.Column("browser_word_count", sa.Integer(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("content_family", sa.String(length=255), nullable=True),
        sa.Column("selection_reasons", sa.JSON(), nullable=True),
        sa.Column("geo_importance_rank", sa.Integer(), nullable=True),
        sa.Column("geo_importance_score", sa.Integer(), nullable=True),
        sa.Column("geo_importance_signals", sa.JSON(), nullable=True),
    ),
    "website_audit_recommendations": (
        sa.Column("observed_evidence", sa.Text(), nullable=True),
        sa.Column("affected_page_count", sa.Integer(), nullable=True),
        sa.Column("evaluated_page_count", sa.Integer(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
    ),
    "website_audits": (
        sa.Column("candidate_page_limit", sa.Integer(), nullable=True),
        sa.Column("candidate_url_count", sa.Integer(), nullable=True),
        sa.Column("selected_geo_page_count", sa.Integer(), nullable=True),
    ),
}


def _existing_column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_missing_columns(table_name: str, columns: tuple[sa.Column, ...]) -> None:
    existing = _existing_column_names(table_name)
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)
            existing.add(column.name)


def upgrade():
    for table_name, columns in EXPECTED_COLUMNS.items():
        _add_missing_columns(table_name, columns)


def downgrade():
    # Forward-only repair: these fields may be owned by 0024, 0025, or 0026 on
    # different databases. Removing them here could destroy pre-existing data.
    pass
