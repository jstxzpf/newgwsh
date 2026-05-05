from pydantic import BaseModel
from typing import List

class ChatRequest(BaseModel):
    query: str
    context_kb_ids: List[int] = []
    session_id: str | None = None