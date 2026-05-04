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
    # 权限校验契约 (§三)：仅科室负责人或 role_level >= 5
    # 简化：假设已通过 depends 或在此检查
    if current_user.role_level < 5:
        raise BusinessException(403, "无权签批")

    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    
    # 铁律 (§七.3)：状态校验 status == SUBMITTED
    if doc.status != "SUBMITTED":
        raise BusinessException(409, "公文当前不在待审批状态")
        
    log_id = await DocumentService.process_approval(db, doc, req.action, current_user.user_id, req.comments)
    await db.commit()
    
    # 后端设计方案 §一.1：通过时触发 FORMAT 任务
    if req.action == "APPROVE":
        from app.tasks.worker import process_format_task
        process_format_task.delay(doc_id)

    return {"code": 200, "message": "success", "data": {"log_id": log_id}}