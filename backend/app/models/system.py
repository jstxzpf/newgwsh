from sqlalchemy import Column, Integer, String, Enum as SQLEnum, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB
from app.models.enums import TaskType, TaskStatus

class AsyncTask(Base):
    __tablename__ = "async_tasks"
    task_id = Column(String(64), primary_key=True)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    task_status = Column(SQLEnum(TaskStatus), index=True, nullable=False, default=TaskStatus.QUEUED)
    input_params = Column(JSONB, nullable=False, default={})
    retry_count = Column(Integer, nullable=False, default=0)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), nullable=True)
    kb_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    progress_pct = Column(Integer, nullable=False, default=0)
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, index=True, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class NBSWorkflowAudit(Base):
    __tablename__ = "nbs_workflow_audit"
    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    workflow_node_id = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reference_id = Column(Integer, ForeignKey("document_approval_logs.log_id"), nullable=True)
    action_details = Column(JSONB, nullable=True)
    action_timestamp = Column(DateTime, index=True, server_default=func.now())

class DocumentApprovalLog(Base):
    __tablename__ = "document_approval_logs"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), index=True, nullable=False)
    submitter_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    decision_status = Column(String(32), nullable=False)
    rejection_reason = Column(Text, nullable=True)
    sip_hash = Column(String(64), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

class SystemConfig(Base):
    __tablename__ = "system_config"
    config_key = Column(String(64), primary_key=True)
    config_value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    value_type = Column(String(16), nullable=False, default='string')
    updated_by = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class UserNotification(Base):
    __tablename__ = "user_notifications"
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=True)
    type = Column(String(32), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, index=True, nullable=False, default=False)
    created_at = Column(DateTime, index=True, nullable=False, server_default=func.now())