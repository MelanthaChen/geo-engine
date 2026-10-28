"""Durable, idempotent Outreach research jobs and result envelopes."""
from alembic import op
import sqlalchemy as sa
revision='20261027_0029'
down_revision='20260927_0028'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('outreach_research_jobs',sa.Column('id',sa.String(),primary_key=True),sa.Column('request_hash',sa.String(),nullable=False),sa.Column('profile',sa.Text(),nullable=False),sa.Column('status',sa.String(),nullable=False),sa.Column('property_id',sa.Integer()),sa.Column('audit_id',sa.Integer()),sa.Column('opportunity_id',sa.Integer()),sa.Column('experiment_id',sa.Integer()),sa.Column('result',sa.Text()),sa.Column('error',sa.Text()),sa.Column('created_at',sa.String()),sa.Column('updated_at',sa.String()))
    op.create_table('outreach_research_records',sa.Column('id',sa.String(),primary_key=True),sa.Column('kind',sa.String()),sa.Column('profile_id',sa.String()),sa.Column('profile_version',sa.String()),sa.Column('payload',sa.Text(),nullable=False))
    op.create_index('ix_outreach_research_records_kind','outreach_research_records',['kind'])
    op.create_index('ix_outreach_research_records_profile_id','outreach_research_records',['profile_id'])
def downgrade():
    raise RuntimeError('Data-preserving migration: export durable research records before any explicit rollback')
