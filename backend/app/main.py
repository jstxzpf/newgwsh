from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import BusinessException, business_exception_handler, validation_exception_handler
from app.api.v1 import auth, locks, documents, sse, tasks

app = FastAPI(title="泰兴调查队公文处理系统 V3.0")

app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(locks.router, prefix="/api/v1/locks", tags=["分布式锁"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["公文流转"])
app.include_router(sse.router, prefix="/api/v1/sse", tags=["SSE流"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["异步任务"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}