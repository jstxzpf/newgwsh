from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.task import TaskType, TaskStatus

class AsyncTaskRead(BaseModel):
    task_id: str
    task_type: TaskType
    task_status: TaskStatus
    progress_pct: int
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    doc_id: Optional[str] = None
    kb_id: Optional[int] = None
    creator_id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
