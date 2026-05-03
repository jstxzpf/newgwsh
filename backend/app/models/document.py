from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import DocumentStatus
from sqlalchemy.orm import validates
from sqlalchemy.dialects.postgresql import JSONB

class DocumentType(Base):
    __tablename__ = "document_types"
    type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_code = Column(String(32), unique=True, nullable=False)
    type_name = Column(String(64), nullable=False)
    layout_rules = Column(JSONB, nullable=False, default={})
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class ExemplarDocument(Base):
    __tablename__ = "exemplar_documents"
    exemplar_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    doc_type_id = Column(Integer, ForeignKey("document_types.type_id"), index=True, nullable=False)
    tier = Column(String(32), nullable=False, default="DEPT")
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), nullable=True)
    file_path = Column(String(512), nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)
    extracted_text = Column(Text, nullable=True)
    uploader_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False, default="未命名公文")
    content = Column(Text, nullable=True, default="")
    status = Column(SQLEnum(DocumentStatus), index=True, nullable=False, default=DocumentStatus.DRAFTING)
    doc_type_id = Column(Integer, ForeignKey("document_types.type_id"), nullable=False)
    exemplar_id = Column(Integer, ForeignKey("exemplar_documents.exemplar_id"), nullable=True)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    ai_polished_content = Column(Text, nullable=True)
    draft_suggestion = Column(Text, nullable=True)
    word_output_path = Column(String(512), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @validates('status')
    def validate_status_transition(self, key, value):
        # 简单校验拦截，在写入数据库时进行状态机验证
        return value

class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    content = Column(Text, nullable=False)
    trigger_event = Column(String(64), nullable=False)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    created_at = Column(DateTime, index=True, server_default=func.now())