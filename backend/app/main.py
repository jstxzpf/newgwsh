from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import BusinessException, business_exception_handler, validation_exception_handler
from app.api.v1 import auth, locks, documents, sse, tasks, kb_admin, approval, chat, notifications, sys

app = FastAPI(title="泰兴调查队公文处理系统 V3.0")

app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(locks.router, prefix="/api/v1/locks", tags=["分布式锁"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["公文流转"])
app.include_router(sse.router, prefix="/api/v1/sse", tags=["SSE流"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["异步任务"])
app.include_router(kb_admin.router, prefix="/api/v1/kb", tags=["知识库"])
app.include_router(approval.router, prefix="/api/v1/approval", tags=["审批签批"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["智能问答"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["消息通知"])
app.include_router(sys.router, prefix="/api/v1/sys", tags=["系统中枢"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}