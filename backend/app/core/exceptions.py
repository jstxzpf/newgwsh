from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

class BusinessException(Exception):
    def __init__(self, code: int, message: str, error_code: str = None):
        self.code = code
        self.message = message
        self.error_code = error_code

async def business_exception_handler(request: Request, exc: BusinessException):
    content = {"code": exc.code, "message": exc.message}
    if exc.error_code:
        content["error_code"] = exc.error_code
    return JSONResponse(status_code=exc.code, content=content)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "message": "参数校验错误", "data": exc.errors()},
    )