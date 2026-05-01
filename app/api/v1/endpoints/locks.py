from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.api import deps
from app.core.locks import lock_manager
from app.models.org import SystemUser
from app.schemas.response import StandardResponse, success, error

router = APIRouter()

class LockRequest(BaseModel):
    doc_id: str

class HeartbeatRequest(BaseModel):
    doc_id: str
    lock_token: str

@router.post("/acquire", response_model=StandardResponse)
async def acquire_lock(
    req: LockRequest,
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """申请编辑锁"""
    res = await lock_manager.acquire_lock(
        doc_id=req.doc_id,
        user_id=current_user.user_id,
        username=current_user.full_name
    )
    if res:
        return success(data=res)
    return error(code=423, message="Document is locked by another user")

@router.post("/heartbeat", response_model=StandardResponse)
async def heartbeat(
    req: HeartbeatRequest,
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """心跳续租"""
    res = await lock_manager.heartbeat(
        doc_id=req.doc_id,
        token=req.lock_token
    )
    if res:
        return success(data=res)
    return error(code=409, message="Lock expired or invalid token")

class ReleaseRequest(BaseModel):
    doc_id: str
    lock_token: str
    content: Optional[str] = None

@router.post("/release", response_model=StandardResponse)
async def release_lock(
    req: ReleaseRequest,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """释放锁 (支持 beforeunload 合并保存 P7.2)"""
    # 1. 如果包含内容，先执行保存 (原子合并防止竞态)
    if req.content is not None:
        from app.models.document import Document
        doc = await db.get(Document, req.doc_id)
        if doc and not doc.is_deleted:
            # 校验锁归属后才允许保存
            if await lock_manager.verify_lock(req.doc_id, req.lock_token):
                doc.content = req.content
                await db.commit()

    # 2. 释放锁 (内部校验 token)
    success_release = await lock_manager.release_lock(
        doc_id=req.doc_id,
        token=req.lock_token
    )
    
    # 注意契约要求: 如果锁因 TTL 已自然过期不存在，静默返回 200 (API契约 §5)
    return success(message="Lock released")

@router.get("/config", response_model=StandardResponse)
async def get_lock_config(
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取锁配置参数 (P5.4)"""
    from app.core.config import settings
    return success(data={
        "lock_ttl_seconds": settings.LOCK_TTL_DEFAULT,
        "heartbeat_interval_seconds": settings.LOCK_HEARTBEAT_INTERVAL
    })

@router.delete("/{lock_key}", response_model=StandardResponse)
async def force_break_lock(
    lock_key: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """强制斩断锁 (管理员大盘专用 P5.4)"""
    # 这里的 lock_key 应该是 Redis 中的完整 Key，如 lock:uuid
    
    # 1. 提取锁信息以便通知
    lock_data_raw = await lock_manager.redis.get(lock_key)
    if not lock_data_raw:
        return error(code=404, message="Lock key not found")
    
    import json
    lock_data = json.loads(lock_data_raw)
    target_user_id = lock_data.get("user_id")
    doc_id = lock_key.split(":")[-1] if ":" in lock_key else "unknown"

    # 2. 删除锁
    await lock_manager.redis.delete(lock_key)
    
    # 3. 写入审计日志
    from app.models.audit import WorkflowAudit
    audit = WorkflowAudit(
        doc_id=doc_id,
        workflow_node_id=42, 
        operator_id=current_user.user_id,
        action_details={"action": "force_release", "lock_key": lock_key, "evicted_user_id": target_user_id}
    )
    db.add(audit)
    await db.commit()
    
    # 4. 推送 SSE 通知被驱逐用户 (契约附录)
    from app.core.sse_utils import publish_user_event
    await publish_user_event(target_user_id, "notification.lock_reclaimed", {
        "doc_id": doc_id,
        "reason": f"Lock force released by administrator {current_user.full_name}"
    })
    
    return success(message=f"Lock {lock_key} force released")
