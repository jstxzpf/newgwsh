from pydantic import BaseModel
from typing import Optional

class ApprovalReviewRequest(BaseModel):
    action: str # APPROVE or REJECT
    comments: Optional[str] = None