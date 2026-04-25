from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import DocumentStatus, WorkflowNode, TaskType, TaskStatus

class Document(Base):
    __tablename__ = "documents"
    
    doc_id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False, default="未命名公文")
    content = Column(Text, nullable=True, default="")
    status = Column(Enum(DocumentStatus), index=True, nullable=False, default=DocumentStatus.DRAFTING)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    ai_polished_content = Column(Text, nullable=True)
    draft_suggestion = Column(Text, nullable=True)
    word_output_path = Column(String(512), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"
    
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    content = Column(Text, nullable=False)
    trigger_event = Column(String(64), nullable=False)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    created_at = Column(DateTime, index=True, server_default=func.now())

class DocumentApprovalLog(Base):
    __tablename__ = "document_approval_logs"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), index=True, nullable=False)
    submitter_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    decision_status = Column(String(64), nullable=False)  # APPROVED or REJECTED
    rejection_reason = Column(Text, nullable=True)
    sip_hash = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, server_default=func.now(), nullable=False)

class WorkflowAudit(Base):
    __tablename__ = "nbs_workflow_audit"
    
    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    workflow_node_id = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reference_id = Column(Integer, ForeignKey("document_approval_logs.log_id"), nullable=True)
    action_details = Column(JSONB, nullable=True)
    action_timestamp = Column(DateTime, index=True, server_default=func.now())

class AsyncTask(Base):
    __tablename__ = "async_tasks"
    
    task_id = Column(String(64), primary_key=True)
    task_type = Column(Enum(TaskType), nullable=False)
    task_status = Column(Enum(TaskStatus), index=True, nullable=False, default=TaskStatus.QUEUED)
    input_params = Column(JSONB, nullable=False, default={})
    retry_count = Column(Integer, nullable=False, default=0)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), nullable=True)
    kb_id = Column(Integer, nullable=True) # Explicit foreign key omitted to avoid circular import dependency issue for now, will link logical.
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    progress_pct = Column(Integer, nullable=False, default=0)
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, index=True, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
