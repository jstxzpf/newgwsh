from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.document import DocStatus

class DocumentBase(BaseModel):
    title: str = "未命名公文"
    doc_type_id: int

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    doc_type_id: Optional[int] = None

class DocumentAutoSave(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    draft_content: Optional[str] = None # 用于 DIFF 模式下的建议稿二改
    lock_token: Optional[str] = None # 用于锁验证

class DocumentRead(DocumentBase):
    doc_id: str
    status: DocStatus
    content: Optional[str] = None
    creator_id: int
    dept_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentDetail(DocumentRead):
    ai_polished_content: Optional[str] = None
    draft_suggestion: Optional[str] = None
    word_output_path: Optional[str] = None
    doc_type_name: Optional[str] = None
