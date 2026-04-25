from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.document_service import DocumentService
from app.core.locks import LockService
from pydantic import BaseModel
from typing import Optional
import uuid
import json
from app.tasks.worker import dummy_polish_task
from app.models.document import AsyncTask
from app.core.enums import TaskType, TaskStatus
from app.core.redis import redis_client

router = APIRouter()

class AutoSaveRequest(BaseModel):
    content: Optional[str] = None
    draft_content: Optional[str] = None

@router.post("/{doc_id}/auto-save")
async def auto_save_document(
    doc_id: str, 
    payload: AutoSaveRequest, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        doc = await DocumentService.auto_save(db, doc_id, payload.content, payload.draft_content)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/lock")
async def acquire_document_lock(doc_id: str, user_id: int, username: str):
    # TODO: user_id should be extracted from Auth Token
    token = await LockService.acquire_lock(doc_id, user_id, username)
    if not token:
        raise HTTPException(status_code=409, detail="Document is being edited by another user")
    return {"lock_token": token}

@router.post("/{doc_id}/unlock")
async def release_document_lock(doc_id: str, lock_token: str):
    success = await LockService.release_lock(doc_id, lock_token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid token or lock already released")
    return {"status": "success"}

@router.post("/{doc_id}/heartbeat")
async def heartbeat_document_lock(doc_id: str, lock_token: str):
    success = await LockService.heartbeat(doc_id, lock_token)
    if not success:
        raise HTTPException(status_code=409, detail="Lock lost or invalid token")
    return {"status": "success"}

@router.post("/{doc_id}/polish")
async def trigger_polish(doc_id: str, user_id: int, db: AsyncSession = Depends(get_async_db)):
    # 1. 持久化任务记录
    task_id = str(uuid.uuid4())
    new_task = AsyncTask(
        task_id=task_id,
        task_type=TaskType.POLISH,
        doc_id=doc_id,
        creator_id=user_id,
        task_status=TaskStatus.QUEUED
    )
    db.add(new_task)
    await db.commit()
    
    # 2. 派发 Celery 任务
    dummy_polish_task.apply_async(args=[doc_id], task_id=task_id)
    
    # 3. 初始状态同步 Redis
    await redis_client.set(f"task_status:{task_id}", json.dumps({
        "progress": 0,
        "status": TaskStatus.QUEUED,
        "result": None
    }), ex=3600)
    
    return {"task_id": task_id}
