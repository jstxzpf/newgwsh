"""Initial migration

Revision ID: 0f99c030af5e
Revises: 
Create Date: 2026-05-04 02:10:46.034112

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector

# revision identifiers, used by Alembic.
revision = '0f99c030af5e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0. 启用 pgvector 扩展
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # 1. 创建无循环依赖的基础表
    op.create_table('document_types',
    sa.Column('type_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('type_code', sa.String(length=32), nullable=False),
    sa.Column('type_name', sa.String(length=64), nullable=False),
    sa.Column('layout_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('type_id'),
    sa.UniqueConstraint('type_code')
    )
    op.create_table('knowledge_physical_files',
    sa.Column('file_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('file_path', sa.String(length=512), nullable=False),
    sa.Column('file_size', sa.BIGINT(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('file_id')
    )
    op.create_index(op.f('ix_knowledge_physical_files_content_hash'), 'knowledge_physical_files', ['content_hash'], unique=True)
    
    # 2. 创建 departments (先不加对 system_users 的外键)
    op.create_table('departments',
    sa.Column('dept_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('dept_name', sa.String(length=128), nullable=False),
    sa.Column('dept_code', sa.String(length=32), nullable=True),
    sa.Column('dept_head_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('dept_id'),
    sa.UniqueConstraint('dept_code'),
    sa.UniqueConstraint('dept_name')
    )

    # 3. 创建 system_users (依赖 departments)
    op.create_table('system_users',
    sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('full_name', sa.String(length=64), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('dept_id', sa.Integer(), nullable=True),
    sa.Column('role_level', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dept_id'], ['departments.dept_id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_system_users_dept_id'), 'system_users', ['dept_id'], unique=False)
    op.create_index(op.f('ix_system_users_username'), 'system_users', ['username'], unique=True)

    # 4. 现在补全 departments 对 system_users 的外键
    op.create_foreign_key('fk_dept_head', 'departments', 'system_users', ['dept_head_id'], ['user_id'])

    # 5. 其余表按顺序创建
    op.create_table('exemplar_documents',
    sa.Column('exemplar_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('doc_type_id', sa.Integer(), nullable=False),
    sa.Column('tier', sa.String(length=32), nullable=False),
    sa.Column('dept_id', sa.Integer(), nullable=True),
    sa.Column('file_path', sa.String(length=512), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('extracted_text', sa.Text(), nullable=True),
    sa.Column('uploader_id', sa.Integer(), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dept_id'], ['departments.dept_id'], ),
    sa.ForeignKeyConstraint(['doc_type_id'], ['document_types.type_id'], ),
    sa.ForeignKeyConstraint(['uploader_id'], ['system_users.user_id'], ),
    sa.PrimaryKeyConstraint('exemplar_id')
    )
    
    op.create_table('knowledge_base_hierarchy',
    sa.Column('kb_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('kb_name', sa.String(length=255), nullable=False),
    sa.Column('kb_type', sa.Enum('FILE', 'DIRECTORY', name='kbtypeenum'), nullable=False),
    sa.Column('kb_tier', sa.Enum('BASE', 'DEPT', 'PERSONAL', name='kbtier'), nullable=False),
    sa.Column('dept_id', sa.Integer(), nullable=True),
    sa.Column('security_level', sa.Enum('CORE', 'IMPORTANT', 'GENERAL', name='datasecuritylevel'), nullable=False),
    sa.Column('parse_status', sa.String(length=32), nullable=False),
    sa.Column('physical_file_id', sa.Integer(), nullable=True),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dept_id'], ['departments.dept_id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['system_users.user_id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['knowledge_base_hierarchy.kb_id'], ),
    sa.ForeignKeyConstraint(['physical_file_id'], ['knowledge_physical_files.file_id'], ),
    sa.PrimaryKeyConstraint('kb_id')
    )
    
    op.create_table('system_config',
    sa.Column('config_key', sa.String(length=64), nullable=False),
    sa.Column('config_value', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('value_type', sa.String(length=16), nullable=False),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['updated_by'], ['system_users.user_id'], ),
    sa.PrimaryKeyConstraint('config_key')
    )
    
    op.create_table('users_sessions',
    sa.Column('session_id', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('refresh_token_hash', sa.String(length=255), nullable=False),
    sa.Column('access_jti', sa.String(length=64), nullable=True),
    sa.Column('device_info', sa.String(length=255), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['system_users.user_id'], ),
    sa.PrimaryKeyConstraint('session_id')
    )

    op.create_table('documents',
    sa.Column('doc_id', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('DRAFTING', 'SUBMITTED', 'APPROVED', 'REJECTED', name='documentstatus'), nullable=False),
    sa.Column('doc_type_id', sa.Integer(), nullable=False),
    sa.Column('exemplar_id', sa.Integer(), nullable=True),
    sa.Column('dept_id', sa.Integer(), nullable=True),
    sa.Column('creator_id', sa.Integer(), nullable=False),
    sa.Column('ai_polished_content', sa.Text(), nullable=True),
    sa.Column('draft_suggestion', sa.Text(), nullable=True),
    sa.Column('word_output_path', sa.String(length=512), nullable=True),
    sa.Column('reviewer_id', sa.Integer(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['creator_id'], ['system_users.user_id'], ),
    sa.ForeignKeyConstraint(['dept_id'], ['departments.dept_id'], ),
    sa.ForeignKeyConstraint(['doc_type_id'], ['document_types.type_id'], ),
    sa.ForeignKeyConstraint(['exemplar_id'], ['exemplar_documents.exemplar_id'], ),
    sa.ForeignKeyConstraint(['reviewer_id'], ['system_users.user_id'], ),
    sa.PrimaryKeyConstraint('doc_id')
    )

    op.create_table('knowledge_chunks',
    sa.Column('chunk_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('kb_id', sa.Integer(), nullable=False),
    sa.Column('physical_file_id', sa.Integer(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True), # 兼容 pgvector 处理，稍后手动修正为 vector 类型
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('kb_tier', sa.Enum('BASE', 'DEPT', 'PERSONAL', name='kbtier'), nullable=False),
    sa.Column('security_level', sa.Enum('CORE', 'IMPORTANT', 'GENERAL', name='datasecuritylevel'), nullable=False),
    sa.Column('dept_id', sa.Integer(), nullable=True),
    sa.Column('owner_id', sa.Integer(), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['dept_id'], ['departments.dept_id'], ),
    sa.ForeignKeyConstraint(['kb_id'], ['knowledge_base_hierarchy.kb_id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['system_users.user_id'], ),
    sa.ForeignKeyConstraint(['physical_file_id'], ['knowledge_physical_files.file_id'], ),
    sa.PrimaryKeyConstraint('chunk_id')
    )
    # 手动修正 embedding 字段为 vector(1024)
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1024)")

    op.create_table('async_tasks',
    sa.Column('task_id', sa.String(length=64), nullable=False),
    sa.Column('task_type', sa.Enum('POLISH', 'FORMAT', 'PARSE', name='tasktype'), nullable=False),
    sa.Column('task_status', sa.Enum('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='taskstatus'), nullable=False),
    sa.Column('input_params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('doc_id', sa.String(length=64), nullable=True),
    sa.Column('kb_id', sa.Integer(), nullable=True),
    sa.Column('creator_id', sa.Integer(), nullable=False),
    sa.Column('progress_pct', sa.Integer(), nullable=False),
    sa.Column('result_summary', sa.Text(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['system_users.user_id'], ),
    sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ),
    sa.ForeignKeyConstraint(['kb_id'], ['knowledge_base_hierarchy.kb_id'], ),
    sa.PrimaryKeyConstraint('task_id')
    )

    op.create_table('document_approval_logs',
    sa.Column('log_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('doc_id', sa.String(length=64), nullable=False),
    sa.Column('submitter_id', sa.Integer(), nullable=False),
    sa.Column('reviewer_id', sa.Integer(), nullable=True),
    sa.Column('decision_status', sa.String(length=32), nullable=False),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('sip_hash', sa.String(length=64), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ),
    sa.ForeignKeyConstraint(['reviewer_id'], ['system_users.user_id'], ),
    sa.ForeignKeyConstraint(['submitter_id'], ['system_users.user_id'], ),
    sa.PrimaryKeyConstraint('log_id')
    )

    op.create_table('document_snapshots',
    sa.Column('snapshot_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('doc_id', sa.String(length=64), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('trigger_event', sa.String(length=64), nullable=False),
    sa.Column('creator_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['creator_id'], ['system_users.user_id'], ),
    sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ),
    sa.PrimaryKeyConstraint('snapshot_id')
    )

    op.create_table('user_notifications',
    sa.Column('notification_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('doc_id', sa.String(length=64), nullable=True),
    sa.Column('type', sa.Enum('TASK_COMPLETED', 'TASK_FAILED', 'DOC_APPROVED', 'DOC_REJECTED', 'LOCK_RECLAIMED', name='notificationtype'), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['system_users.user_id'], ),
    sa.PrimaryKeyConstraint('notification_id')
    )

    op.create_table('nbs_workflow_audit',
    sa.Column('audit_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('doc_id', sa.String(length=64), nullable=False),
    sa.Column('workflow_node_id', sa.Integer(), nullable=False),
    sa.Column('operator_id', sa.Integer(), nullable=False),
    sa.Column('reference_id', sa.Integer(), nullable=True),
    sa.Column('action_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('action_timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ),
    sa.ForeignKeyConstraint(['operator_id'], ['system_users.user_id'], ),
    sa.ForeignKeyConstraint(['reference_id'], ['document_approval_logs.log_id'], ),
    sa.PrimaryKeyConstraint('audit_id')
    )

    # 6. 建立索引 (含手动修复的 GIN 索引)
    op.create_index('idx_chunk_content_gin', 'knowledge_chunks', [sa.text("to_tsvector('simple', content)")], unique=False, postgresql_using='gin', postgresql_where=sa.text('is_deleted = false'))
    op.execute("CREATE INDEX idx_chunk_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops) WHERE is_deleted = false")
    op.create_index('idx_chunk_metadata_gin', 'knowledge_chunks', ['metadata_json'], unique=False, postgresql_using='gin')
    
    op.create_index('idx_doc_dept_status', 'documents', ['dept_id', 'status'], unique=False, postgresql_where=sa.text('is_deleted = false'))
    op.create_index('idx_kb_hierarchy_owner_tier', 'knowledge_base_hierarchy', ['owner_id', 'kb_tier'], unique=False, postgresql_where=sa.text('is_deleted = false'))
    op.create_index('idx_kb_personal_unique', 'knowledge_base_hierarchy', ['physical_file_id', 'owner_id'], unique=True, postgresql_where=sa.text("kb_type = 'FILE' AND kb_tier = 'PERSONAL' AND is_deleted = false"))


def downgrade() -> None:
    pass
