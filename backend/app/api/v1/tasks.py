from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.system import AsyncTask
from app.schemas.task import PolishTaskRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.locks import redis_client
from app.services.task_service import TaskService

router = APIRouter()

@router.post("/polish")
async def trigger_polish(req: PolishTaskRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task_id = await TaskService.trigger_polish_task(db, req.doc_id, current_user.user_id, req.model_dump())
    await db.commit()
    
    # 写入 Redis 用于 SSE 权限绑定
    await redis_client.set(f"task_owner:{task_id}", current_user.user_id, ex=86400)
    
    return {"code": 202, "message": "accepted", "data": {"task_id": task_id}}

@router.post("/format")
async def trigger_format(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task_id = await TaskService.trigger_format_task(db, doc_id, current_user.user_id)
    await db.commit()
    await redis_client.set(f"task_owner:{task_id}", current_user.user_id, ex=86400)
    return {"code": 202, "message": "accepted", "data": {"task_id": task_id}}

@router.post("/{task_id}/retry")
async def retry_task(task_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role_level < 99:
        raise BusinessException(403, "仅管理员可重试任务")
        
    await TaskService.retry_failed_task(db, task_id)
    await db.commit()
    return {"code": 200, "message": "任务已重新入队", "data": None}

@router.get("/{task_id}")
async def get_task_status(task_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
    task = result.scalars().first()
    if not task:
        raise BusinessException(404, "任务不存在")
    return {"code": 200, "message": "success", "data": {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "task_status": task.task_status,
        "progress_pct": task.progress_pct,
        "result_summary": task.result_summary,
        "error_message": task.error_message
    }}