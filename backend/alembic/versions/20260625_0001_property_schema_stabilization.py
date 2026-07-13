"""property schema stabilization

Revision ID: 20260625_0001
Revises:
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa

from app.core.database import Base
from app.models import *


revision = "20260625_0001"
down_revision = None
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


def _add_column_if_missing(table_name: str, column: sa.Column):
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    if not _table_exists("properties"):
        op.create_table(
            "properties",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("domain", sa.String(), nullable=False),
            sa.Column("brand_name", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_properties_domain",
            "properties",
            ["domain"],
            unique=True,
        )
    else:
        _add_column_if_missing(
            "properties",
            sa.Column("description", sa.Text(), nullable=True),
        )

    if _table_exists("content_history_events") and not _table_exists(
        "history_events"
    ):
        op.rename_table("content_history_events", "history_events")

    if not _table_exists("history_events"):
        op.create_table(
            "history_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "property_id",
                sa.Integer(),
                sa.ForeignKey("properties.id"),
                nullable=True,
            ),
            sa.Column(
                "content_id",
                sa.Integer(),
                sa.ForeignKey("contents.id"),
                nullable=True,
            ),
            sa.Column(
                "faq_id",
                sa.Integer(),
                sa.ForeignKey("faqs.id"),
                nullable=True,
            ),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
    else:
        _add_column_if_missing(
            "history_events",
            sa.Column("faq_id", sa.Integer(), nullable=True),
        )
        _add_column_if_missing(
            "history_events",
            sa.Column("metadata_json", sa.Text(), nullable=True),
        )

        if _column_exists("history_events", "details"):
            op.execute(
                """
                UPDATE history_events
                SET metadata_json = details
                WHERE metadata_json IS NULL
                """
            )

    for table_name in [
        "faq_sets",
        "contents",
        "publish_tasks",
        "citation_tests",
    ]:
        if _table_exists(table_name):
            _add_column_if_missing(
                table_name,
                sa.Column(
                    "property_id",
                    sa.Integer(),
                    sa.ForeignKey("properties.id"),
                    nullable=True,
                ),
            )

    _add_column_if_missing(
        "contents",
        sa.Column(
            "faq_set_id",
            sa.Integer(),
            sa.ForeignKey("faq_sets.id"),
            nullable=True,
        ),
    )
    _add_column_if_missing(
        "contents",
        sa.Column(
            "faq_id",
            sa.Integer(),
            sa.ForeignKey("faqs.id"),
            nullable=True,
        ),
    )
    _add_column_if_missing(
        "contents",
        sa.Column("publish_platform", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "contents",
        sa.Column("publish_url", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "contents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        """
        UPDATE contents
        SET publish_platform = COALESCE(publish_platform, publish_provider),
            publish_url = COALESCE(publish_url, published_url)
        """
    )

    if _table_exists("generated_contents"):
        op.execute(
            """
            INSERT INTO contents (
                property_id,
                faq_set_id,
                title,
                content_type,
                strategy_type,
                generation_mode,
                target_url,
                faq_source,
                angle,
                perspective,
                archetype,
                internet_style,
                generated_angles,
                body,
                target_persona,
                status,
                publish_status,
                created_at
            )
            SELECT
                property_id,
                source_faq_set_id,
                title,
                content_type,
                content_type,
                'content_generation',
                website_url,
                faq_source,
                angle,
                perspective,
                archetype,
                internet_style,
                generated_angles,
                body,
                category,
                'draft',
                'draft',
                COALESCE(created_at, generation_timestamp, now())
            FROM generated_contents
            WHERE content_id IS NULL
            """
        )
        op.drop_table("generated_contents")

    _add_column_if_missing(
        "citation_tests",
        sa.Column("prompt", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "citation_tests",
        sa.Column("target_brand", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "citation_tests",
        sa.Column("status", sa.String(), nullable=True),
    )
    _add_column_if_missing(
        "citation_tests",
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "citation_tests",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        """
        UPDATE citation_tests
        SET prompt = COALESCE(prompt, query),
            status = COALESCE(status, 'finished'),
            last_run = COALESCE(last_run, tested_at)
        """
    )

    if _table_exists("citations"):
        op.execute(
            """
            INSERT INTO citation_tests (
                property_id,
                content_id,
                platform,
                query,
                prompt,
                status,
                ai_response,
                mentioned,
                evidence_found,
                citation_type,
                tested_at,
                last_run,
                created_at
            )
            SELECT
                contents.property_id,
                citations.content_id,
                citations.platform,
                citations.query_used,
                citations.query_used,
                'finished',
                citations.response_snippet,
                citations.cited,
                citations.cited,
                CASE
                    WHEN citations.cited THEN 'legacy_citation'
                    ELSE 'none'
                END,
                citations.tested_at,
                citations.tested_at,
                COALESCE(citations.tested_at, now())
            FROM citations
            LEFT JOIN contents
                ON contents.id = citations.content_id
            """
        )
        op.drop_table("citations")

    if not _table_exists("citation_results"):
        op.create_table(
            "citation_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "citation_test_id",
                sa.Integer(),
                sa.ForeignKey("citation_tests.id"),
                nullable=False,
            ),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("mentioned", sa.Boolean(), nullable=True),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column("response", sa.Text(), nullable=True),
            sa.Column(
                "tested_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
        op.execute(
            """
            INSERT INTO citation_results (
                citation_test_id,
                model,
                mentioned,
                rank,
                response,
                tested_at
            )
            SELECT
                id,
                COALESCE(platform, 'openai'),
                mentioned,
                NULL,
                ai_response,
                COALESCE(tested_at, now())
            FROM citation_tests
            WHERE ai_response IS NOT NULL
            """
        )


def downgrade():
    if _table_exists("citation_results"):
        op.drop_table("citation_results")

    if _table_exists("history_events") and not _table_exists(
        "content_history_events"
    ):
        op.rename_table("history_events", "content_history_events")
