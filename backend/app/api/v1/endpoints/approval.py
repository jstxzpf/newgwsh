from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.document_service import DocumentService
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ReviewRequest(BaseModel):
    is_approved: bool
    rejection_reason: Optional[str] = None

@router.post("/{doc_id}/review")
async def review_document(
    doc_id: str,
    payload: ReviewRequest,
    reviewer_id: int = 5, # TODO: Get from Token, must be role_level >= 5
    db: AsyncSession = Depends(get_async_db)
):
    try:
        await DocumentService.review_document(db, doc_id, reviewer_id, payload.is_approved, payload.rejection_reason)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
