from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.core.redis import redis_client
from app.models.document import WorkflowAudit
from app.core.database import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import WorkflowNode
import json

router = APIRouter()

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
    admin_id: int = 99, # 临时 mock 管理员
    role_level: int = 1, # TODO: 从 Token 中获取
    db: AsyncSession = Depends(get_async_db)
):
    if role_level < 99:
        raise HTTPException(status_code=403, detail="Permission denied. Admin only.")

    if not lock_key.startswith("lock:"):
        lock_key = f"lock:{lock_key}"
        
    current_lock = await redis_client.get(lock_key)
    if not current_lock:
        raise HTTPException(status_code=404, detail="Lock not found or already expired")
        
    await redis_client.delete(lock_key)
    
    # 写入审计日志
    doc_id = lock_key.replace("lock:", "")
    audit = WorkflowAudit(
        doc_id=doc_id,
        workflow_node_id=WorkflowNode.REVISION, # 暂借用
        operator_id=admin_id,
        action_details={"note": f"管理员强拆锁，被驱逐用户: {json.loads(current_lock).get('username')}"}
    )
    db.add(audit)
    await db.commit()
    
    return {"status": "success", "message": "Lock forcefully removed"}
