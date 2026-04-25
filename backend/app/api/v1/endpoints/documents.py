from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.document_service import DocumentService
from app.core.locks import LockService
from pydantic import BaseModel
from typing import Optional

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
