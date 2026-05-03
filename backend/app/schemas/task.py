from pydantic import BaseModel
from typing import List, Optional

class PolishTaskRequest(BaseModel):
    doc_id: str
    context_kb_ids: List[int] = []
    context_snapshot_version: Optional[int] = None
    exemplar_id: Optional[int] = None

class FormatTaskRequest(BaseModel):
    doc_id: str