from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserInfoResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    role_level: int
    dept_id: int | None
    department_name: str | None = None
    is_dept_head: bool = False