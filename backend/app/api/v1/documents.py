from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.schemas.document import DocumentInitRequest, AutoSaveRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.services.document_service import DocumentService

router = APIRouter()

@router.post("/init")
async def init_document(req: DocumentInitRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc_id = await DocumentService.init_document(db, req.title, req.doc_type_id, current_user.user_id, current_user.dept_id)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"doc_id": doc_id}}

@router.get("/{doc_id}")
async def get_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    return {
        "code": 200, 
        "message": "success", 
        "data": {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "content": doc.content,
            "status": doc.status,
            "doc_type_id": doc.doc_type_id,
            "ai_polished_content": doc.ai_polished_content,
            "draft_suggestion": doc.draft_suggestion
        }
    }

@router.post("/{doc_id}/auto-save")
async def auto_save(doc_id: str, req: AutoSaveRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc or doc.is_deleted:
        raise BusinessException(404, "公文不存在")
    if doc.status != "DRAFTING":
        raise BusinessException(409, "当前状态不可保存")
        
    await DocumentService.auto_save_draft(db, doc, req.title, req.content, req.draft_content)
    await db.commit()
    return {"code": 200, "message": "success", "data": None}