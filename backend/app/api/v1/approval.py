from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.schemas.approval import ApprovalReviewRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.services.document_service import DocumentService

router = APIRouter()

@router.post("/{doc_id}/review")
async def review_document(doc_id: str, req: ApprovalReviewRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    if doc.status != "SUBMITTED":
        raise BusinessException(409, "公文当前不在待审批状态")
        
    await DocumentService.process_approval(db, doc, req.action, current_user.user_id, req.comments)
    await db.commit()
    
    return {"code": 200, "message": "success", "data": None}