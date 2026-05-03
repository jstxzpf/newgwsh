from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.models.system import DocumentApprovalLog, NBSWorkflowAudit
from app.schemas.approval import ApprovalReviewRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.sip import generate_sip_hash
from datetime import datetime, timezone

router = APIRouter()

@router.post("/{doc_id}/review")
async def review_document(doc_id: str, req: ApprovalReviewRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 权限应限定为科室负责人，为简化暂略
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    if doc.status != "SUBMITTED":
        raise BusinessException(409, "公文当前不在待审批状态")
        
    now = datetime.now(timezone.utc)
    
    if req.action == "APPROVE":
        doc.status = "APPROVED"
        sip = generate_sip_hash(doc.content or "", current_user.user_id, now.isoformat())
        log = DocumentApprovalLog(
            doc_id=doc_id, submitter_id=doc.creator_id, reviewer_id=current_user.user_id,
            decision_status="APPROVED", sip_hash=sip, reviewed_at=now
        )
    elif req.action == "REJECT":
        if not req.comments:
            raise BusinessException(400, "驳回必须提供理由")
        doc.status = "REJECTED"
        log = DocumentApprovalLog(
            doc_id=doc_id, submitter_id=doc.creator_id, reviewer_id=current_user.user_id,
            decision_status="REJECTED", rejection_reason=req.comments, reviewed_at=now
        )
    else:
        raise BusinessException(400, "无效的审批动作")
        
    doc.reviewer_id = current_user.user_id
    db.add(log)
    await db.flush()
    
    audit = NBSWorkflowAudit(
        doc_id=doc_id, workflow_node_id=40 if req.action == "APPROVE" else 41,
        operator_id=current_user.user_id, reference_id=log.log_id,
        action_details={"reason": req.comments} if req.comments else {}
    )
    db.add(audit)
    await db.commit()
    
    return {"code": 200, "message": "success", "data": None}