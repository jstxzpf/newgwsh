from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class DepartmentOut(BaseModel):
    dept_id: int
    dept_name: str
    dept_code: str
    dept_head_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DocumentTypeOut(BaseModel):
    type_id: int
    type_name: str
    type_code: str
    layout_rules: Optional[dict] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
