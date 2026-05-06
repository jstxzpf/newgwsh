"""Add post-approval workflow: REVIEWED/ARCHIVED statuses, document_number, issuance/archive/dispatch fields, notifications trigger_user_id

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
Create Date: 2026-05-05 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '1b2c3d4e5f6a'
down_revision = '0a1b2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum values (must run outside transaction)
    op.execute("COMMIT")
    op.execute("ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'REVIEWED'")
    op.execute("ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'ARCHIVED'")
    op.execute("BEGIN")

    # Add new columns to documents table
    op.add_column('documents', sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('system_users.user_id'), nullable=True))
    op.add_column('documents', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('document_number', sa.String(length=64), nullable=True))
    op.add_column('documents', sa.Column('issued_by', sa.Integer(), sa.ForeignKey('system_users.user_id'), nullable=True))
    op.add_column('documents', sa.Column('issued_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('archived_by', sa.Integer(), sa.ForeignKey('system_users.user_id'), nullable=True))
    op.add_column('documents', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('dispatch_depts', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add trigger_user_id to user_notifications
    op.add_column('user_notifications', sa.Column('trigger_user_id', sa.Integer(), sa.ForeignKey('system_users.user_id'), nullable=True))

    # Create index on document_number for lookup
    op.create_index('idx_document_number', 'documents', ['document_number'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_document_number', table_name='documents')

    op.drop_column('user_notifications', 'trigger_user_id')

    op.drop_column('documents', 'dispatch_depts')
    op.drop_column('documents', 'archived_at')
    op.drop_column('documents', 'archived_by')
    op.drop_column('documents', 'issued_at')
    op.drop_column('documents', 'issued_by')
    op.drop_column('documents', 'document_number')
    op.drop_column('documents', 'reviewed_at')
    op.drop_column('documents', 'reviewed_by')

    # Note: cannot remove enum values from PostgreSQL enum type,
    # so downgrade does not attempt to remove REVIEWED/ARCHIVED from documentstatus
