from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum

class ApprovalAction(str, Enum):
    APPROVE = "APPROVED"
    REJECT = "REJECTED"

class ApprovalReview(BaseModel):
    action: ApprovalAction
    comments: Optional[str] = None

    @field_validator("comments")
    @classmethod
    def reject_needs_reason(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("action") == ApprovalAction.REJECT and not v:
            raise ValueError("Rejection reason is mandatory")
        return v
