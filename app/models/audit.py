from typing import Optional
from sqlalchemy import String, Enum, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin
from app.models.document import DocStatus

class WorkflowAudit(Base, TimestampMixin):
    """
    工作流审计轨迹表 (Append-Only)
    """
    __tablename__ = "workflow_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doc_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), index=True, comment="公文ID")
    operator_id: Mapped[int] = mapped_column(Integer, index=True, comment="操作人ID")
    action: Mapped[str] = mapped_column(String(50), comment="操作动作")
    from_status: Mapped[DocStatus] = mapped_column(Enum(DocStatus), comment="原状态")
    to_status: Mapped[DocStatus] = mapped_column(Enum(DocStatus), comment="目标状态")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="处理意见/原因")
    trace_id: Mapped[str] = mapped_column(String(64), index=True, comment="链路追踪ID")

class DocumentApprovalLog(Base, TimestampMixin):
    """
    签批环节 SIP 存证日志
    """
    __tablename__ = "document_approval_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doc_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), index=True, comment="公文ID")
    signer_id: Mapped[int] = mapped_column(Integer, index=True, comment="签批人ID")
    sip_fingerprint: Mapped[str] = mapped_column(String(64), comment="SIP 指纹 (HMAC-SHA256)")
    normalized_content_hash: Mapped[str] = mapped_column(String(64), comment="规范化内容哈希")
