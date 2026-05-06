"""Make nbs_workflow_audit.doc_id nullable for KB operations

Revision ID: 0a1b2c3d4e5f
Revises: 0f99c030af5e
Create Date: 2026-05-05 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0a1b2c3d4e5f'
down_revision = '0f99c030af5e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('nbs_workflow_audit', 'doc_id',
        existing_type=sa.String(length=64),
        nullable=True)


def downgrade() -> None:
    op.alter_column('nbs_workflow_audit', 'doc_id',
        existing_type=sa.String(length=64),
        nullable=False)
