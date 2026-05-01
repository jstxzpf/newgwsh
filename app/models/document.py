import enum
import uuid
from typing import Optional, List
from sqlalchemy import String, Enum, Integer, Boolean, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, validates, relationship
from app.models.base import Base, TimestampMixin

class DocStatus(enum.IntEnum):
    DRAFTING = 10    # 起草中
    SUBMITTED = 30   # 已提交待审批
    APPROVED = 40    # 已通过 (终态)
    REJECTED = 41    # 已驳回

class Document(Base, TimestampMixin):
    """公文主表"""
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), comment="公文追踪号(UUID)")
    title: Mapped[str] = mapped_column(String(255), default="未命名公文", index=True, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, default="")
    status: Mapped[DocStatus] = mapped_column(
        Enum(DocStatus), 
        default=DocStatus.DRAFTING,
        index=True,
        nullable=False,
        comment="业务状态"
    )
    doc_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_types.type_id"), nullable=False)
    exemplar_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("exemplar_documents.exemplar_id"), nullable=True)
    dept_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=False)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    
    ai_polished_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="AI润色建议稿")
    draft_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="DIFF模式下的建议稿二改草稿")
    word_output_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="排版产物Word路径")
    reviewer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 关系定义
    doc_type: Mapped["DocumentType"] = relationship("DocumentType")
    creator: Mapped["SystemUser"] = relationship("SystemUser", foreign_keys=[creator_id])
    reviewer: Mapped[Optional["SystemUser"]] = relationship("SystemUser", foreign_keys=[reviewer_id])
    snapshots: Mapped[List["DocumentSnapshot"]] = relationship("DocumentSnapshot", back_populates="document")

    @validates("status")
    def validate_status_transition(self, key, new_status):
        if not hasattr(self, "status") or self.status is None:
            return new_status
        
        old_status = self.status
        if old_status == new_status:
            return new_status

        # 状态机转换规则对照《实施约束规则》
        valid_transitions = {
            DocStatus.DRAFTING: [DocStatus.SUBMITTED],
            DocStatus.SUBMITTED: [DocStatus.APPROVED, DocStatus.REJECTED],
            DocStatus.REJECTED: [DocStatus.DRAFTING],
            DocStatus.APPROVED: [],  # 终态
        }

        if new_status not in valid_transitions.get(old_status, []):
            raise ValueError(f"Illegal status transition: {old_status.name} -> {new_status.name}")
        
        return new_status

class DocumentSnapshot(Base, TimestampMixin):
    """公文历史快照表"""
    __tablename__ = "document_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="快照内容")
    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False, comment="触发事件(如accept_polish)")
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)

    # 关系定义
    document: Mapped["Document"] = relationship("Document", back_populates="snapshots")

class ExemplarDocument(Base, TimestampMixin):
    """参考范文库"""
    __tablename__ = "exemplar_documents"

    exemplar_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_types.type_id"), index=True, nullable=False)
    
    # 范文层级：仅限 BASE (管理员) 和 DEPT (科室负责人)
    tier: Mapped[str] = mapped_column(String(20), default="DEPT", nullable=False, comment="BASE或DEPT")
    dept_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("departments.dept_id"), nullable=True)
    
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="提取的纯文本用于few-shot")
    uploader_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 关系定义
    doc_type: Mapped["DocumentType"] = relationship("DocumentType")
