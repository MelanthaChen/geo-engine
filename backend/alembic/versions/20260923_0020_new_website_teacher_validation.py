"""persist new-website Teacher Validation source provenance

Revision ID: 20260923_0020
Revises: 20260923_0019
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260923_0020"
down_revision = "20260923_0019"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    query_columns = {
        column["name"] for column in inspector.get_columns("experiment_queries")
    }
    document_columns = {
        column["name"] for column in inspector.get_columns("experiment_documents")
    }
    query_additions = (
        sa.Column("query_policy_version", sa.String(length=100), nullable=True),
        sa.Column("source_audit_id", sa.Integer(), nullable=True),
        sa.Column("supporting_evidence_json", sa.Text(), nullable=True),
        sa.Column("retrieval_provider", sa.String(length=100), nullable=True),
        sa.Column("retrieval_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    for column in query_additions:
        if column.name not in query_columns:
            op.add_column("experiment_queries", column)

    foreign_keys = {
        tuple(foreign_key.get("constrained_columns") or ())
        for foreign_key in inspector.get_foreign_keys("experiment_queries")
    }
    if ("source_audit_id",) not in foreign_keys:
        op.create_foreign_key(
            "fk_experiment_queries_source_audit_id",
            "experiment_queries", "website_audits", ["source_audit_id"], ["id"],
            ondelete="SET NULL",
        )

    document_additions = (
        sa.Column("source_role", sa.String(length=30), nullable=True),
        sa.Column("retrieval_provider", sa.String(length=100), nullable=True),
        sa.Column("retrieval_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
    )
    for column in document_additions:
        if column.name not in document_columns:
            op.add_column("experiment_documents", column)


def downgrade():
    for column in ("content_sha256", "retrieval_timestamp", "retrieval_provider", "source_role"):
        op.drop_column("experiment_documents", column)
    op.drop_constraint("fk_experiment_queries_source_audit_id", "experiment_queries", type_="foreignkey")
    for column in ("retrieval_timestamp", "retrieval_provider", "supporting_evidence_json", "source_audit_id", "query_policy_version"):
        op.drop_column("experiment_queries", column)
