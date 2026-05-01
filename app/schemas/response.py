from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    """统一 API 响应结构"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

def success(data: Any = None, message: str = "success") -> StandardResponse:
    return StandardResponse(code=200, message=message, data=data)

def error(code: int = 400, message: str = "error", data: Any = None) -> StandardResponse:
    return StandardResponse(code=code, message=message, data=data)
