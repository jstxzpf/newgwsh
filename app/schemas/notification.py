from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class NotificationOut(BaseModel):
    notification_id: int
    user_id: int
    doc_id: Optional[str] = None
    type: str
    content: Optional[str] = None
    is_read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
