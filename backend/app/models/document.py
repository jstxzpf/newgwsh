from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, validates, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from app.models.enums import DocumentStatus
from datetime import datetime

VALID_TRANSITIONS = {
    DocumentStatus.DRAFTING: [DocumentStatus.SUBMITTED],
    DocumentStatus.SUBMITTED: [DocumentStatus.REVIEWED, DocumentStatus.REJECTED],
    DocumentStatus.REVIEWED: [DocumentStatus.APPROVED, DocumentStatus.REJECTED],
    DocumentStatus.APPROVED: [DocumentStatus.ARCHIVED],
    DocumentStatus.ARCHIVED: [],
    DocumentStatus.REJECTED: [DocumentStatus.DRAFTING],
}

class DocumentType(Base):
    __tablename__ = "document_types"
    type_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    type_name: Mapped[str] = mapped_column(String(64), nullable=False)
    layout_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())

class ExemplarDocument(Base):
    __tablename__ = "exemplar_documents"
    exemplar_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_types.type_id"), index=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="DEPT")
    dept_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.dept_id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploader_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    doc_type = relationship("DocumentType")
    uploader = relationship("SystemUser")

class Document(Base):
    __tablename__ = "documents"
    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名公文")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    status: Mapped[DocumentStatus] = mapped_column(SQLEnum(DocumentStatus), index=True, nullable=False, default=DocumentStatus.DRAFTING)
    doc_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_types.type_id"), nullable=False)
    exemplar_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("exemplar_documents.exemplar_id"), nullable=True)
    dept_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.dept_id"), index=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    ai_polished_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issued_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dispatch_depts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("SystemUser", foreign_keys=[creator_id], back_populates="documents")
    doc_type = relationship("DocumentType")
    exemplar = relationship("ExemplarDocument")
    reviewer = relationship("SystemUser", foreign_keys=[reviewer_id])
    reviewed_by_user = relationship("SystemUser", foreign_keys=[reviewed_by])
    issued_by_user = relationship("SystemUser", foreign_keys=[issued_by])
    archived_by_user = relationship("SystemUser", foreign_keys=[archived_by])
    snapshots = relationship("DocumentSnapshot", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "idx_doc_dept_status",
            dept_id,
            status,
            postgresql_where=(is_deleted == False),
        ),
    )

    @validates('status')
    def validate_status_transition(self, key, value):
        if self.status and value != self.status:
            if value not in VALID_TRANSITIONS.get(self.status, []):
                raise ValueError(f"Invalid transition from {self.status} to {value}")
        return value

class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"
    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    created_at: Mapped[func.now] = mapped_column(DateTime, index=True, server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="snapshots")
    creator = relationship("SystemUser")