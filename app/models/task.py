import enum
from sqlalchemy import String, Enum, Integer, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.models.base import Base, TimestampMixin

class TaskType(enum.Enum):
    POLISH = "POLISH"
    FORMAT = "FORMAT"
    PARSE = "PARSE"

class TaskStatus(enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AsyncTask(Base, TimestampMixin):
    """异步任务持久化表"""
    __tablename__ = "async_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="Celery任务ID")
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False)
    task_status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.QUEUED, index=True, nullable=False)
    
    input_params: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}', nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    doc_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("documents.doc_id"), nullable=True)
    kb_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), nullable=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    started_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
