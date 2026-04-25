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
from app.models.document import AsyncTask, DocumentApprovalLog, Document
from app.core.enums import TaskType, TaskStatus, DocumentStatus
from app.core.redis import redis_client
from app.api.dependencies import ai_rate_limiter
from app.services.sip_service import SIPService
from sqlalchemy import select

router = APIRouter()

class AutoSaveRequest(BaseModel):
    content: Optional[str] = None
    draft_content: Optional[str] = None
    model_config = {"extra": "forbid"}

class InitRequest(BaseModel):
    title: str

@router.post("/init")
async def init_document(
    payload: InitRequest,
    user_id: int = 1, 
    dept_id: int = 1, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        doc_id = await DocumentService.init_document(db, payload.title, user_id, dept_id)
        return {"doc_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{doc_id}/submit")
async def submit_document(
    doc_id: str,
    user_id: int = 1, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        await DocumentService.submit_document(db, doc_id, user_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/revise")
async def revise_document(
    doc_id: str,
    user_id: int = 1, 
    username: str = "测试科员",
    db: AsyncSession = Depends(get_async_db)
):
    try:
        result = await DocumentService.revise_document(db, doc_id, user_id, username)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/{doc_id}/auto-save")
async def auto_save_document(
    doc_id: str, 
    payload: AutoSaveRequest, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        payload_keys = payload.model_dump(exclude_unset=True).keys()
        doc = await DocumentService.auto_save(db, doc_id, payload.content, payload.draft_content, "content" in payload_keys)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/lock")
async def acquire_document_lock(doc_id: str, user_id: int, username: str):
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

class ApplyPolishRequest(BaseModel):
    final_content: Optional[str] = None

@router.post("/{doc_id}/apply-polish")
async def apply_document_polish(
    doc_id: str, 
    payload: ApplyPolishRequest,
    user_id: int = 1, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        await DocumentService.apply_polish(db, doc_id, user_id, payload.final_content)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/discard-polish")
async def discard_document_polish(
    doc_id: str, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        await DocumentService.discard_polish(db, doc_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/polish", dependencies=[Depends(ai_rate_limiter)])
async def trigger_polish(
    doc_id: str, 
    user_id: int, 
    lock_token: str, # 颗粒度对齐：必须凭锁触发
    db: AsyncSession = Depends(get_async_db)
):
    # 校验锁持有权
    lock_key = f"lock:{doc_id}"
    lock_data_raw = await redis_client.get(lock_key)
    if not lock_data_raw:
        raise HTTPException(status_code=409, detail="Must hold a lock to trigger AI polish")
    
    lock_data = json.loads(lock_data_raw)
    if lock_data.get("token") != lock_token or lock_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Lock token mismatch or not owner")

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
    
    dummy_polish_task.apply_async(args=[doc_id], task_id=task_id)
    
    await redis_client.set(f"task_status:{task_id}", json.dumps({
        "progress": 0,
        "status": TaskStatus.QUEUED,
        "result": None
    }), ex=3600)
    
    return {"task_id": task_id}

@router.get("/{doc_id}/verify-sip")
async def verify_document_sip(doc_id: str, db: AsyncSession = Depends(get_async_db)):
    stmt = select(DocumentApprovalLog).where(
        DocumentApprovalLog.doc_id == doc_id, 
        DocumentApprovalLog.decision_status == "APPROVED"
    ).order_by(DocumentApprovalLog.reviewed_at.desc()).limit(1)
    
    res = await db.execute(stmt)
    log = res.scalars().first()
    
    if not log or not log.sip_hash:
        return {"is_valid": False, "message": "未找到该公文的有效审批存证记录"}
        
    doc_res = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = doc_res.scalars().first()
    
    if not doc:
        return {"is_valid": False, "message": "公文实体不存在"}
        
    current_hash = SIPService.generate_sip_fingerprint(doc.content, log.reviewer_id, log.reviewed_at)
    
    if current_hash == log.sip_hash:
        return {"is_valid": True, "message": "存证校验通过，内容未被篡改"}
    else:
        return {"is_valid": False, "message": "存证校验失败！内容可能已被篡改"}
