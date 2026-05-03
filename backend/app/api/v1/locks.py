from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.schemas.lock import LockAcquireRequest, LockHeartbeatRequest, LockReleaseRequest
from app.core.locks import acquire_redis_lock, release_redis_lock, extend_redis_lock
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import uuid

router = APIRouter()

@router.post("/acquire")
async def acquire_lock(req: LockAcquireRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == req.doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    if doc.status != "DRAFTING":
        raise BusinessException(409, "公文已流转，不可编辑", "READONLY_IMMUTABLE")
    
    token = str(uuid.uuid4())
    success = await acquire_redis_lock(req.doc_id, current_user.user_id, current_user.username, token, ttl=180)
    if not success:
        raise BusinessException(423, "公文正在被他人编辑，当前只读", "READONLY_CONFLICT")
        
    return {"code": 200, "message": "success", "data": {"lock_token": token, "ttl": 180}}

@router.post("/heartbeat")
async def heartbeat_lock(req: LockHeartbeatRequest, current_user: SystemUser = Depends(get_current_user)):
    success = await extend_redis_lock(req.doc_id, current_user.user_id, req.lock_token, ttl=180)
    if not success:
        raise BusinessException(403, "锁已失效或被夺", "LOCK_RECLAIMED")
    return {"code": 200, "message": "success", "data": {"next_suggested_heartbeat": 90, "lock_ttl_remaining": 180}}

@router.post("/release")
async def release_lock(req: LockReleaseRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if req.content is not None:
        # 如果包含 content，执行自动保存合并操作
        result = await db.execute(select(Document).where(Document.doc_id == req.doc_id))
        doc = result.scalars().first()
        if doc and doc.status == "DRAFTING":
            doc.content = req.content
            await db.commit()
            
    await release_redis_lock(req.doc_id, current_user.user_id, req.lock_token)
    return {"code": 200, "message": "success", "data": None}

@router.get("/config")
async def get_lock_config(current_user: SystemUser = Depends(get_current_user)):
    return {"code": 200, "message": "success", "data": {"lock_ttl_seconds": 180, "heartbeat_interval_seconds": 90}}