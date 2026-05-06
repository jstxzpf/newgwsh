from sqlalchemy import Column, Integer, String, Enum as SQLEnum, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from app.models.enums import TaskType, TaskStatus, NotificationType
from datetime import datetime

class AsyncTask(Base):
    __tablename__ = "async_tasks"
    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType), nullable=False)
    task_status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), index=True, nullable=False, default=TaskStatus.QUEUED)
    input_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    doc_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("documents.doc_id"), nullable=True)
    kb_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), nullable=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[func.now] = mapped_column(DateTime, index=True, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    creator = relationship("SystemUser")
    document = relationship("Document")
    kb_node = relationship("KnowledgeBaseHierarchy")

class NBSWorkflowAudit(Base):
    __tablename__ = "nbs_workflow_audit"
    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=True)
    workflow_node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reference_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("document_approval_logs.log_id"), nullable=True)
    action_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    action_timestamp: Mapped[func.now] = mapped_column(DateTime, index=True, server_default=func.now())

    # Relationships
    document = relationship("Document")
    operator = relationship("SystemUser")
    approval_log = relationship("DocumentApprovalLog")

class DocumentApprovalLog(Base):
    __tablename__ = "document_approval_logs"
    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    submitter_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reviewer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    decision_status: Mapped[str] = mapped_column(String(32), nullable=False) # SUBMITTED/APPROVED/REJECTED
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    document = relationship("Document")
    submitter = relationship("SystemUser", foreign_keys=[submitter_id])
    reviewer = relationship("SystemUser", foreign_keys=[reviewer_id])

class SystemConfig(Base):
    __tablename__ = "system_config"
    config_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    config_value: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False, default='string')
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    updated_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class UserNotification(Base):
    __tablename__ = "user_notifications"
    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    trigger_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    doc_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=True)
    type: Mapped[NotificationType] = mapped_column(SQLEnum(NotificationType), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False, default=False)
    created_at: Mapped[func.now] = mapped_column(DateTime, index=True, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("SystemUser", foreign_keys=[user_id])
    trigger_user = relationship("SystemUser", foreign_keys=[trigger_user_id])
    document = relationship("Document")