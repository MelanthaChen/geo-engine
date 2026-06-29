"""ensure history events link to website audits

Revision ID: 20260628_0006
Revises: 20260626_0005
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260628_0006"
down_revision = "20260626_0005"
branch_labels = None
depends_on = None


FOREIGN_KEY_NAME = "fk_history_events_website_audit_id"
INDEX_NAME = "ix_history_events_website_audit_id"


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


def _foreign_key_exists(
    table_name: str,
    constrained_columns: list[str],
    referred_table: str,
):
    return _foreign_key_name(
        table_name=table_name,
        constrained_columns=constrained_columns,
        referred_table=referred_table,
    ) is not None


def _foreign_key_name(
    table_name: str,
    constrained_columns: list[str],
    referred_table: str,
):
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if table_name not in inspector.get_table_names():
        return None

    for foreign_key in inspector.get_foreign_keys(table_name):
        if (
            foreign_key.get("constrained_columns") == constrained_columns
            and foreign_key.get("referred_table") == referred_table
        ):
            return foreign_key.get("name")

    return None


def upgrade():
    if not _table_exists("history_events"):
        raise RuntimeError("history_events table must exist before this migration")

    if not _table_exists("website_audits"):
        raise RuntimeError("website_audits table must exist before this migration")

    if not _column_exists("history_events", "website_audit_id"):
        with op.batch_alter_table("history_events") as batch_op:
            batch_op.add_column(
                sa.Column("website_audit_id", sa.Integer(), nullable=True),
            )

    if not _foreign_key_exists(
        table_name="history_events",
        constrained_columns=["website_audit_id"],
        referred_table="website_audits",
    ):
        with op.batch_alter_table("history_events") as batch_op:
            batch_op.create_foreign_key(
                FOREIGN_KEY_NAME,
                "website_audits",
                ["website_audit_id"],
                ["id"],
            )

    if not _index_exists("history_events", INDEX_NAME):
        op.create_index(
            INDEX_NAME,
            "history_events",
            ["website_audit_id"],
            unique=False,
        )


def downgrade():
    if _index_exists("history_events", INDEX_NAME):
        op.drop_index(INDEX_NAME, table_name="history_events")

    foreign_key_name = _foreign_key_name(
        table_name="history_events",
        constrained_columns=["website_audit_id"],
        referred_table="website_audits",
    )

    if foreign_key_name:
        with op.batch_alter_table("history_events") as batch_op:
            batch_op.drop_constraint(
                foreign_key_name,
                type_="foreignkey",
            )

    if _column_exists("history_events", "website_audit_id"):
        with op.batch_alter_table("history_events") as batch_op:
            batch_op.drop_column("website_audit_id")
