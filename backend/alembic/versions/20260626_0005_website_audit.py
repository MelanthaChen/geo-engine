"""website audit storage

Revision ID: 20260626_0005
Revises: 20260626_0004
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0005"
down_revision = "20260626_0004"
branch_labels = None
depends_on = None


def _table_exists(table_name: str):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str):
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if table_name not in inspector.get_table_names():
        return False

    return column_name in [
        column["name"]
        for column in inspector.get_columns(table_name)
    ]


def _index_exists(table_name: str, index_name: str):
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if table_name not in inspector.get_table_names():
        return False

    return index_name in [
        index["name"]
        for index in inspector.get_indexes(table_name)
    ]


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]):
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade():
    if not _table_exists("website_audits"):
        op.create_table(
            "website_audits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "property_id",
                sa.Integer(),
                sa.ForeignKey("properties.id"),
                nullable=False,
            ),
            sa.Column("base_url", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("brand_summary", sa.Text(), nullable=True),
            sa.Column("product_summary", sa.Text(), nullable=True),
            sa.Column("target_audience", sa.Text(), nullable=True),
            sa.Column("primary_use_cases", sa.Text(), nullable=True),
            sa.Column("core_value_proposition", sa.Text(), nullable=True),
            sa.Column("overall_geo_score", sa.Integer(), nullable=True),
            sa.Column("content_coverage_score", sa.Integer(), nullable=True),
            sa.Column("faq_coverage_score", sa.Integer(), nullable=True),
            sa.Column("internal_linking_score", sa.Integer(), nullable=True),
            sa.Column("website_structure_score", sa.Integer(), nullable=True),
            sa.Column("brand_clarity_score", sa.Integer(), nullable=True),
            sa.Column("trust_signals_score", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )

    for index_name, columns in [
        ("ix_website_audits_property_id", ["property_id"]),
        ("ix_website_audits_status", ["status"]),
    ]:
        _create_index_if_missing("website_audits", index_name, columns)

    if not _table_exists("website_pages"):
        op.create_table(
            "website_pages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "audit_id",
                sa.Integer(),
                sa.ForeignKey("website_audits.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("page_title", sa.Text(), nullable=True),
            sa.Column("meta_description", sa.Text(), nullable=True),
            sa.Column("h1", sa.Text(), nullable=True),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "internal_link_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "external_link_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "discovered_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )

    _create_index_if_missing(
        "website_pages",
        "ix_website_pages_audit_id",
        ["audit_id"],
    )

    if not _table_exists("website_audit_recommendations"):
        op.create_table(
            "website_audit_recommendations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "audit_id",
                sa.Integer(),
                sa.ForeignKey("website_audits.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("priority", sa.String(), nullable=False),
            sa.Column("evidence_url", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )

    for index_name, columns in [
        ("ix_website_audit_recommendations_audit_id", ["audit_id"]),
        ("ix_website_audit_recommendations_category", ["category"]),
    ]:
        _create_index_if_missing(
            "website_audit_recommendations",
            index_name,
            columns,
        )

    if not _column_exists("history_events", "website_audit_id"):
        op.add_column(
            "history_events",
            sa.Column(
                "website_audit_id",
                sa.Integer(),
                sa.ForeignKey("website_audits.id"),
                nullable=True,
            ),
        )

    _create_index_if_missing(
        "history_events",
        "ix_history_events_website_audit_id",
        ["website_audit_id"],
    )


def downgrade():
    if _index_exists("history_events", "ix_history_events_website_audit_id"):
        op.drop_index(
            "ix_history_events_website_audit_id",
            table_name="history_events",
        )

    if _column_exists("history_events", "website_audit_id"):
        op.drop_column("history_events", "website_audit_id")

    if _table_exists("website_audit_recommendations"):
        op.drop_table("website_audit_recommendations")

    if _table_exists("website_pages"):
        op.drop_table("website_pages")

    if _table_exists("website_audits"):
        op.drop_table("website_audits")
