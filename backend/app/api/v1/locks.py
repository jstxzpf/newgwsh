from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import SystemUser
from app.schemas.lock import LockAcquireRequest, LockHeartbeatRequest, LockReleaseRequest
from app.api.dependencies import get_current_user
from app.services.lock_service import LockService
from app.core.config import settings
from app.core.exceptions import BusinessException

router = APIRouter()

@router.post("/acquire")
async def acquire_lock(req: LockAcquireRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    token = await LockService.acquire_lock(db, req.doc_id, current_user.user_id, current_user.username)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"lock_token": token, "ttl": settings.LOCK_TTL}}

@router.post("/heartbeat")
async def heartbeat_lock(req: LockHeartbeatRequest, current_user: SystemUser = Depends(get_current_user)):
    interval = await LockService.heartbeat(req.doc_id, current_user.user_id, req.lock_token)
    return {"code": 200, "message": "success", "data": {
        "next_suggested_heartbeat": interval, 
        "lock_ttl_remaining": settings.LOCK_TTL
    }}

@router.post("/release")
async def release_lock(req: LockReleaseRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await LockService.release_lock(db, req.doc_id, current_user.user_id, req.lock_token, req.content)
    return {"code": 200, "message": "success", "data": None}

@router.delete("/{doc_id}")
async def force_reclaim_lock(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 权限校验：管理员 (§五.5)
    if current_user.role_level < 99:
        raise BusinessException(403, "无权强制释放锁")
    
    await LockService.force_release(db, doc_id, current_user.user_id)
    await db.commit()
    return {"code": 200, "message": "success", "data": None}

@router.get("/config")
async def get_lock_config(current_user: SystemUser = Depends(get_current_user)):
    return {"code": 200, "message": "success", "data": {
        "lock_ttl_seconds": settings.LOCK_TTL, 
        "heartbeat_interval_seconds": settings.HEARTBEAT_INTERVAL
    }}