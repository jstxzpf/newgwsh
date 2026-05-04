from pydantic import BaseModel
from typing import List, Optional

class DocumentInitRequest(BaseModel):
    title: str = "未命名公文"
    doc_type_id: int

class AutoSaveRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    draft_content: Optional[str] = None

class ApplyPolishRequest(BaseModel):
    final_content: str

class SnapshotCreateRequest(BaseModel):
    content: str
    trigger_event: str = "manual"