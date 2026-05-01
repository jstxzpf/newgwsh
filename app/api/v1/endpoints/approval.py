from typing import Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.document import Document, DocStatus
from app.models.org import SystemUser
from app.models.audit import DocumentApprovalLog, WorkflowAudit
from app.schemas.approval import ApprovalReview, ApprovalAction
from app.schemas.response import StandardResponse, success, error
from app.core.sip import generate_sip_hash

router = APIRouter()

@router.post("/{doc_id}/review", response_model=StandardResponse)
async def review_document(
    doc_id: str,
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_active_user),
    review_in: ApprovalReview
) -> Any:
    """公文审批 (批准/驳回)"""
    
    # 1. 权限校验: 必须是科长(5)及以上，且属于同一科室（除非超管）
    if current_user.role_level < 5:
        raise HTTPException(status_code=403, detail="Not enough permissions for approval")

    stmt = select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error(code=404, message="Document not found")
        
    # 2. 状态校验: 必须是 SUBMITTED(30)
    if doc.status != DocStatus.SUBMITTED:
        return error(code=409, message=f"Document status is {doc.status.name}, cannot review")

    # 3. 开启显式事务 (P5.1 铁律)
    async with db.begin():
        log_entry = DocumentApprovalLog(
            doc_id=doc.doc_id,
            submitter_id=doc.creator_id,
            reviewer_id=current_user.user_id,
            decision_status=review_in.action.value,
            rejection_reason=review_in.comments if review_in.action == ApprovalAction.REJECT else None
        )
        db.add(log_entry)
        
        # 4. 执行状态转换
        if review_in.action == ApprovalAction.APPROVE:
            doc.status = DocStatus.APPROVED
            # 生成 SIP 存证
            reviewed_at_str = datetime.now(timezone.utc).isoformat()
            doc_content = doc.content or ""
            sip_hash = generate_sip_hash(doc_content, current_user.user_id, reviewed_at_str)
            log_entry.sip_hash = sip_hash
            log_entry.reviewed_at = datetime.fromisoformat(reviewed_at_str)
        else:
            doc.status = DocStatus.REJECTED
        
    # 6. 触发异步排版任务 (FORMAT) 和 SSE 通知
    from app.core.sse_utils import publish_user_event
    import asyncio
    from app.core.database import AsyncSessionLocal
    
    # 异步写入审计日志 (实施约束规则 5 推荐方案 B)
    async def write_audit_log_async(doc_id: str, node_id: int, operator_id: int, details: dict):
        async with AsyncSessionLocal() as audit_db:
            audit = WorkflowAudit(
                doc_id=doc_id,
                workflow_node_id=node_id,
                operator_id=operator_id,
                action_details=details
            )
            audit_db.add(audit)
            await audit_db.commit()

    audit_node = 40 if review_in.action == ApprovalAction.APPROVE else 41
    asyncio.create_task(write_audit_log_async(
        doc.doc_id, 
        audit_node, 
        current_user.user_id, 
        {"comments": review_in.comments}
    ))
    
    if review_in.action == ApprovalAction.APPROVE:
        from app.tasks.worker import format_document
        from app.models.task import AsyncTask, TaskType
        
        task = format_document.delay(doc.doc_id)
        
        # 记录异步任务
        async_task = AsyncTask(
            task_id=task.id,
            task_type=TaskType.FORMAT,
            creator_id=current_user.user_id,
            doc_id=doc.doc_id
        )
        db.add(async_task)
        await db.commit()
        
        # 推送 SSE: notification.approved (契约附录)
        await publish_user_event(doc.creator_id, "notification.approved", {
            "doc_id": doc.doc_id,
            "title": doc.title
        })
    else:
        # 推送 SSE: notification.rejected
        await publish_user_event(doc.creator_id, "notification.rejected", {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "rejection_reason": review_in.comments
        })
    
    return success(message=f"Document {review_in.action.value}D successfully")
