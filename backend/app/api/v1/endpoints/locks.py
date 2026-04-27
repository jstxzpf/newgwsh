from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.core.config import settings
from app.models.document import WorkflowAudit
from app.core.database import get_async_db
from app.core.locks import LockService
from app.api.dependencies import get_current_user
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import WorkflowNode, DocumentStatus
from app.services.document_service import DocumentService
from app.services.audit_service import AuditService
from typing import List, Dict
import json
from app.core.redis import get_redis

router = APIRouter()

@router.get("/")
async def list_all_locks(current_user: User = Depends(get_current_user)):
    if current_user.role_level < 99: # 【对齐修复】必须为超级管理员
        raise HTTPException(status_code=403, detail="Permission denied. Admin only.")
    
    # 扫描 Redis 中所有以 lock: 开头的键
    redis_client = await get_redis()
    keys = await redis_client.keys("lock:*")
    locks = []
    for key in keys:
        val = await redis_client.get(key)
        if val:
            data = json.loads(val)
            data["doc_id"] = key.replace("lock:", "")
            locks.append(data)
    return {"locks": locks}

@router.post("/acquire")
async def acquire_lock_aligned(
    doc_id: str, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # 【对齐修复】强制状态校验
    if doc.status != DocumentStatus.DRAFTING:
        raise HTTPException(status_code=403, detail=f"Cannot lock document in '{doc.status.value}' state")

    token = await LockService.acquire_lock(doc_id, current_user.user_id, current_user.username)
    if not token:
        raise HTTPException(status_code=409, detail="Lock already held")
    return {"lock_token": token}

@router.post("/release")
async def release_lock_aligned(
    doc_id: str, 
    lock_token: str,
    current_user: User = Depends(get_current_user)
):
    # 安全校验：确保只有锁持有者才能释放锁
    redis_client = await get_redis()
    lock_key = f"lock:{doc_id}"
    lock_data_raw = await redis_client.get(lock_key)
    if lock_data_raw:
        lock_data = json.loads(lock_data_raw)
        if lock_data.get("user_id") != current_user.user_id:
            raise HTTPException(status_code=403, detail="Cannot unlock other's document")

    success = await LockService.release_lock(doc_id, lock_token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"status": "success"}

@router.post("/heartbeat")
async def heartbeat_aligned(
    doc_id: str, 
    lock_token: str,
    current_user: User = Depends(get_current_user)
):
    success = await LockService.heartbeat(doc_id, lock_token)
    if not success:
        raise HTTPException(status_code=409, detail="Lock lost")
    return {"status": "success"}

@router.get("/config")
async def get_lock_config():
    return {
        "lock_ttl_seconds": settings.LOCK_TTL_SECONDS,
        "heartbeat_interval_seconds": settings.HEARTBEAT_INTERVAL_SECONDS,
        "retry_backoff_base_seconds": settings.RETRY_BACKOFF_BASE_SECONDS,
        "retry_backoff_max_seconds": settings.RETRY_BACKOFF_MAX_SECONDS
    }

@router.delete("/{lock_key}")
async def force_release_lock(
    lock_key: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Permission denied. Admin only.")

    if not lock_key.startswith("lock:"):
        lock_key = f"lock:{lock_key}"
        
    redis_client = await get_redis()
    current_lock = await redis_client.get(lock_key)
    if not current_lock:
        raise HTTPException(status_code=404, detail="Lock not found or already expired")
        
    await redis_client.delete(lock_key)
    
    # 【解耦修复】改用 BackgroundTasks 异步写入审计
    doc_id = lock_key.replace("lock:", "")
    msg = f"管理员强拆锁，被驱逐用户: {json.loads(current_lock).get('username')}"
    background_tasks.add_task(AuditService.write_audit_log, doc_id, WorkflowNode.REVISION, current_user.user_id, {"note": msg})
    
    return {"status": "success", "message": "Lock forcefully removed"}
