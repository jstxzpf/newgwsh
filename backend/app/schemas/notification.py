from pydantic import BaseModel

class NotificationReadRequest(BaseModel):
    notification_id: int