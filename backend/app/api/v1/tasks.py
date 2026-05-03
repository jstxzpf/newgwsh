from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.models.system import AsyncTask
from app.schemas.task import PolishTaskRequest, FormatTaskRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.locks import redis_client
from app.tasks.worker import dummy_polish_task
import uuid

router = APIRouter()

@router.post("/polish")
async def trigger_polish(req: PolishTaskRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 幂等拦截
    result = await db.execute(select(AsyncTask).where(
        AsyncTask.doc_id == req.doc_id, 
        AsyncTask.task_type == "POLISH",
        AsyncTask.task_status.in_(["QUEUED", "PROCESSING"])
    ))
    existing_task = result.scalars().first()
    if existing_task:
        return {"code": 202, "message": "任务已在进行中", "data": {"task_id": existing_task.task_id}}

    doc_result = await db.execute(select(Document).where(Document.doc_id == req.doc_id))
    doc = doc_result.scalars().first()
    if not doc or doc.status != "DRAFTING":
        raise BusinessException(409, "当前状态不可润色")

    task_id = str(uuid.uuid4())
    new_task = AsyncTask(
        task_id=task_id,
        task_type="POLISH",
        doc_id=req.doc_id,
        creator_id=current_user.user_id,
        input_params=req.model_dump()
    )
    db.add(new_task)
    await db.commit()
    
    # 写入 Redis 用于 SSE 权限绑定
    await redis_client.set(f"task_owner:{task_id}", current_user.user_id, ex=86400) # 1天TTL
    
    # 派发 Celery 任务
    dummy_polish_task.delay(task_id, req.doc_id)
    
    return {"code": 202, "message": "accepted", "data": {"task_id": task_id}}

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