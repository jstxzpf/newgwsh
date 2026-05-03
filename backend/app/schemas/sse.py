from pydantic import BaseModel

class TicketRequest(BaseModel):
    task_id: str