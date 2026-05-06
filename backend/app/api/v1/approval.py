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
async def review_document(
    doc_id: str, req: ApprovalReviewRequest,
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """科长审核：SUBMITTED → REVIEWED / REJECTED (role_level >= 5)"""
    if current_user.role_level < 5:
        raise BusinessException(403, "无权签批")

    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")

    if doc.status.value not in ("SUBMITTED", "REVIEWED"):
        raise BusinessException(409, "公文当前不在待审核/待签发状态")

    log_id = await DocumentService.process_review(
        db, doc, req.action, current_user.user_id, req.comments
    )
    await db.commit()

    return {"code": 200, "message": "success", "data": {"log_id": log_id, "new_status": doc.status.value}}


@router.post("/{doc_id}/issue")
async def issue_document(
    doc_id: str,
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """局长签发：REVIEWED → APPROVED，自动生成发文编号 (role_level >= 99)"""
    if current_user.role_level < 99:
        raise BusinessException(403, "仅局长/管理员可签发公文")

    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")

    log_id = await DocumentService.issue_document(db, doc, current_user.user_id)
    await db.commit()

    # Trigger FORMAT task for docx generation
    from app.tasks.worker import process_format_task
    process_format_task.delay(doc_id)

    return {
        "code": 200, "message": "success",
        "data": {
            "log_id": log_id,
            "document_number": doc.document_number,
            "new_status": "APPROVED"
        }
    }
