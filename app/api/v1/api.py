from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, documents, locks, kb, chat, approval, sse, sys, exemplars, tasks,
    users, departments, doc_types, audit, notifications
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(locks.router, prefix="/locks", tags=["locks"])
api_router.include_router(kb.router, prefix="/kb", tags=["kb"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(approval.router, prefix="/approval", tags=["approval"])
api_router.include_router(sse.router, prefix="/sse", tags=["sse"])
api_router.include_router(sys.router, prefix="/sys", tags=["sys"])
api_router.include_router(exemplars.router, prefix="/exemplars", tags=["exemplars"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(doc_types.router, prefix="/doc-types", tags=["doc-types"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
