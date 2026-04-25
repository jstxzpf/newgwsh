from fastapi import APIRouter
from app.api.v1.endpoints import documents, sse, kb_admin, chat, approval, sys, locks, audit, auth

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(sse.router, prefix="/sse", tags=["sse"])
api_router.include_router(kb_admin.router, prefix="/kb", tags=["kb"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(approval.router, prefix="/approval", tags=["approval"])
api_router.include_router(sys.router, prefix="/sys", tags=["sys"])
api_router.include_router(locks.router, prefix="/locks", tags=["locks"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
