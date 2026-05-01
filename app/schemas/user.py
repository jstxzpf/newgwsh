from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    username: str
    full_name: str
    dept_id: int
    role_level: int = 1
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    dept_id: Optional[int] = None
    role_level: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class User(UserBase):
    user_id: int

    class Config:
        from_attributes = True
