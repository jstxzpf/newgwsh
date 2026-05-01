from sqlalchemy import String, Integer, Text, ForeignKey, Boolean, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.models.base import Base, TimestampMixin

class WorkflowAudit(Base, TimestampMixin):
    """工作流合规审计表 (Append-Only)"""
    __tablename__ = "nbs_workflow_audit"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=True)
    workflow_node_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="工作流节点代号(10, 11, 20...等)")
    operator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("document_approval_logs.log_id"), nullable=True, comment="关联审批日志ID")
    action_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="操作详情JSONB")
    action_timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

class DocumentApprovalLog(Base, TimestampMixin):
    """公文签批存证表 (Append-Only)"""
    __tablename__ = "document_approval_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    submitter_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reviewer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    decision_status: Mapped[str] = mapped_column(String(20), nullable=False, comment="APPROVED或REJECTED")
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="SIP防篡改指纹")
    submitted_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserNotification(Base, TimestampMixin):
    """用户消息通知表"""
    __tablename__ = "user_notifications"

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    doc_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("documents.doc_id"), nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, comment="通知类型: TASK_COMPLETED等")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="通知内容或JSON")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
