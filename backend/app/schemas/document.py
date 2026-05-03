from pydantic import BaseModel
from typing import Optional

class DocumentInitRequest(BaseModel):
    doc_type_id: int
    title: str

class AutoSaveRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    draft_content: Optional[str] = None