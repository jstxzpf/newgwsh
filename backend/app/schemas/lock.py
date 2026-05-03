from pydantic import BaseModel
from typing import Optional

class LockAcquireRequest(BaseModel):
    doc_id: str

class LockHeartbeatRequest(BaseModel):
    doc_id: str
    lock_token: str

class LockReleaseRequest(BaseModel):
    doc_id: str
    lock_token: str
    content: Optional[str] = None