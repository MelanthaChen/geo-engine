"""workflow integration jobs citation runs history refs

Revision ID: 20260626_0003
Revises: 20260625_0002
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0003"
down_revision = "20260625_0002"
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
    if not _table_exists("publishing_jobs"):
        op.create_table(
            "publishing_jobs",
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
                nullable=False,
            ),
            sa.Column(
                "account_id",
                sa.Integer(),
                sa.ForeignKey("accounts.id"),
                nullable=False,
            ),
            sa.Column("platform", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("logs", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
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

    for index_name, columns in [
        ("ix_publishing_jobs_property_id", ["property_id"]),
        ("ix_publishing_jobs_content_id", ["content_id"]),
        ("ix_publishing_jobs_account_id", ["account_id"]),
        ("ix_publishing_jobs_status", ["status"]),
    ]:
        _create_index_if_missing("publishing_jobs", index_name, columns)

    if not _table_exists("citation_test_runs"):
        op.create_table(
            "citation_test_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "property_id",
                sa.Integer(),
                sa.ForeignKey("properties.id"),
                nullable=True,
            ),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("target_brand", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )

    for index_name, columns in [
        ("ix_citation_test_runs_property_id", ["property_id"]),
        ("ix_citation_test_runs_status", ["status"]),
    ]:
        _create_index_if_missing("citation_test_runs", index_name, columns)

    if not _table_exists("citation_test_results"):
        op.create_table(
            "citation_test_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "run_id",
                sa.Integer(),
                sa.ForeignKey("citation_test_runs.id"),
                nullable=False,
            ),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("mentioned", sa.Boolean(), nullable=True),
            sa.Column("rank", sa.Integer(), nullable=True),
            sa.Column("response_snippet", sa.Text(), nullable=True),
            sa.Column("raw_response", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "tested_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )

    for index_name, columns in [
        ("ix_citation_test_results_run_id", ["run_id"]),
        ("ix_citation_test_results_status", ["status"]),
    ]:
        _create_index_if_missing("citation_test_results", index_name, columns)

    for column in [
        sa.Column(
            "publishing_job_id",
            sa.Integer(),
            sa.ForeignKey("publishing_jobs.id"),
            nullable=True,
        ),
        sa.Column(
            "citation_test_run_id",
            sa.Integer(),
            sa.ForeignKey("citation_test_runs.id"),
            nullable=True,
        ),
    ]:
        if not _column_exists("history_events", column.name):
            op.add_column("history_events", column)

    for index_name, columns in [
        ("ix_history_events_publishing_job_id", ["publishing_job_id"]),
        ("ix_history_events_citation_test_run_id", ["citation_test_run_id"]),
    ]:
        _create_index_if_missing("history_events", index_name, columns)


def downgrade():
    for index_name in [
        "ix_history_events_publishing_job_id",
        "ix_history_events_citation_test_run_id",
    ]:
        if _index_exists("history_events", index_name):
            op.drop_index(index_name, table_name="history_events")

    for column_name in ["citation_test_run_id", "publishing_job_id"]:
        if _column_exists("history_events", column_name):
            op.drop_column("history_events", column_name)

    if _table_exists("citation_test_results"):
        op.drop_table("citation_test_results")

    if _table_exists("citation_test_runs"):
        op.drop_table("citation_test_runs")

    if _table_exists("publishing_jobs"):
        op.drop_table("publishing_jobs")
