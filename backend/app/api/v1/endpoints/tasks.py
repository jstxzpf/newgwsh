from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_async_db
from app.models.document import AsyncTask
from app.core.enums import TaskStatus, TaskType
from app.tasks.worker import dummy_polish_task, parse_kb_file_task, celery_app
from app.api.dependencies import get_current_user
from app.models.user import User
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from app.core.redis import get_redis

router = APIRouter()

@router.get("/")
async def list_tasks(
    status: Optional[TaskStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    stmt = select(AsyncTask).where(AsyncTask.creator_id == current_user.user_id)
    if status:
        stmt = stmt.where(AsyncTask.task_status == status)
    stmt = stmt.order_by(AsyncTask.created_at.desc())
    result = await db.execute(stmt)
    return {"data": result.scalars().all()}

@router.get("/{task_id}")
async def get_task_detail(
    task_id: str, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 优先从 Redis 获取实时状态
    redis_client = await get_redis()
    redis_data = await redis_client.get(f"task_status:{task_id}")
    
    res = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=404)
        
    # 【对齐修复】权限校验：仅本人或管理员可见
    if task.creator_id != current_user.user_id and current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Access denied")

    if redis_data:
        return json.loads(redis_data)
    return task

@router.delete("/{task_id}")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_async_db)):
    res = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
    task = res.scalars().first()
    if not task:
        raise HTTPException(status_code=404)
        
    if task.task_status not in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
        raise HTTPException(status_code=400, detail="Only pending tasks can be cancelled")
        
    # 1. 撤销 Celery 任务
    celery_app.control.revoke(task_id, terminate=True)
    
    # 2. 更新数据库
    task.task_status = TaskStatus.FAILED
    task.error_message = "Cancelled by user"
    
    # 3. 更新 Redis
    redis_client = await get_redis()
    await redis_client.delete(f"task_status:{task_id}")
    
    await db.commit()
    return {"status": "success"}

class RetryRequest(BaseModel):
    file_path: Optional[str] = None

@router.post("/{task_id}/retry")
async def retry_failed_task(
    task_id: str, 
    payload: RetryRequest = RetryRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    res = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
    task = res.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # 【对齐修复】越权防护：仅任务创建者可重试
    if task.creator_id != current_user.user_id and current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Permission denied: not task owner")

    if task.task_status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")
        
    # 重新确定文件路径 (对齐基准：优先使用新提供的路径)
    if task.task_type == TaskType.PARSE:
        file_path = payload.file_path or task.input_params.get("file_path")
        if not file_path or not os.path.exists(file_path):
             raise HTTPException(status_code=422, detail="Original physical file missing, please provide a new file_path")
        # 更新任务参数以防再次失败后再次重试找不到路径
        task.input_params["file_path"] = file_path

    # 重置状态
    task.task_status = TaskStatus.QUEUED
    task.progress_pct = 0
    task.error_message = None
    
    # 同步至 Redis
    redis_client = await get_redis()
    await redis_client.set(f"task_status:{task_id}", json.dumps({
        "progress": 0,
        "status": TaskStatus.QUEUED.value,
        "result": None
    }), ex=3600)
    
    await db.commit()
    
    # 重新分发 Celery 任务
    if task.task_type == TaskType.POLISH:
        dummy_polish_task.apply_async(args=[task.doc_id], task_id=task_id)
    elif task.task_type == TaskType.PARSE:
        parse_kb_file_task.apply_async(args=[task.kb_id, task.input_params.get("file_path")], task_id=task_id)
    elif task.task_type == TaskType.FORMAT:
        from app.tasks.worker import format_document_task
        format_document_task.apply_async(args=[task.doc_id], task_id=task_id)
    
    return {"status": "success", "message": "Task queued for retry"}

class PolishTaskRequest(BaseModel):
    doc_id: str
    context_kb_ids: List[int] = []
    lock_token: str

@router.post("/polish")
async def trigger_polish_task(
    payload: PolishTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    from app.api.v1.endpoints.documents import trigger_polish
    # 借用 documents 模块的逻辑实现，保持一致性
    return await trigger_polish(payload.doc_id, payload, payload.lock_token, current_user, db)

class FormatTaskRequest(BaseModel):
    doc_id: str

@router.post("/format")
async def trigger_format_task(
    payload: FormatTaskRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    from app.api.v1.endpoints.documents import trigger_format
    return await trigger_format(payload.doc_id, background_tasks, current_user, db)
