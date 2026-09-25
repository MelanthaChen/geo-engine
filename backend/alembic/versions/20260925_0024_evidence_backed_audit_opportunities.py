"""add evidence-backed audit opportunity fields

Revision ID: 20260925_0024
Revises: 20260925_0023
"""

revision = "20260925_0024"
down_revision = "20260925_0023"
branch_labels = None
depends_on = None


def upgrade():
    # Revision 0001 creates the current model metadata on a clean database, so
    # these evidence fields already exist before this revision is reached.
    pass


def downgrade():
    # The columns are owned by revision 0001 and must survive this downgrade.
    pass
