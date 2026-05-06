from pydantic import BaseModel, Field
from typing import Any, Optional


class ConfigUpdateRequest(BaseModel):
    config_key: str
    config_value: Any


# ── User CRUD ──────────────────────────────────────────────
class UserCreateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    full_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    dept_id: Optional[int] = None
    role_level: int = Field(default=1, ge=1, le=99)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=64)
    dept_id: Optional[int] = None
    role_level: Optional[int] = Field(default=None, ge=1, le=99)
    is_active: Optional[bool] = None


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


# ── Department CRUD ────────────────────────────────────────
class DeptCreateRequest(BaseModel):
    dept_name: str = Field(min_length=1, max_length=128)
    dept_code: Optional[str] = Field(default=None, max_length=32)
    dept_head_id: Optional[int] = None


class DeptUpdateRequest(BaseModel):
    dept_name: Optional[str] = Field(default=None, max_length=128)
    dept_code: Optional[str] = Field(default=None, max_length=32)
    dept_head_id: Optional[int] = None
    is_active: Optional[bool] = None
