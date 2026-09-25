"""add audit discovery provenance

Revision ID: 20260925_0023
Revises: 20260925_0022
"""

revision = "20260925_0023"
down_revision = "20260925_0022"
branch_labels = None
depends_on = None


def upgrade():
    # Revision 0001 calls Base.metadata.create_all() with the current models,
    # so both discovery-provenance columns are already part of a clean schema.
    pass


def downgrade():
    # These columns belong to the schema created by revision 0001. Downgrading
    # across this marker must not remove schema owned by that earlier revision.
    pass
