from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import BusinessException, business_exception_handler, validation_exception_handler
from app.api.v1 import auth

app = FastAPI(title="泰兴调查队公文处理系统 V3.0")

app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}