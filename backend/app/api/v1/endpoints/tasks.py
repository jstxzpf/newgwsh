from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.models.document import AsyncTask
from app.core.enums import TaskStatus, TaskType
from app.tasks.worker import dummy_polish_task, parse_kb_file_task
import json
from app.core.redis import redis_client

router = APIRouter()

@router.post("/{task_id}/retry")
async def retry_failed_task(task_id: str, db: AsyncSession = Depends(get_async_db)):
    from sqlalchemy import select
    res = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
    task = res.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.task_status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")
        
    # 重置状态
    task.task_status = TaskStatus.QUEUED
    task.progress_pct = 0
    task.error_message = None
    
    # 同步至 Redis
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
        file_path = task.input_params.get("file_path")
        parse_kb_file_task.apply_async(args=[task.kb_id, file_path], task_id=task_id)
    
    return {"status": "success", "message": "Task queued for retry"}
