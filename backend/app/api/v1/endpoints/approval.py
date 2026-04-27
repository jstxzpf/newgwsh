from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.document_service import DocumentService
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_current_user
from app.models.user import User, Department
from app.core.enums import DocumentStatus
from sqlalchemy import select

router = APIRouter()

class ReviewRequest(BaseModel):
    is_approved: bool
    rejection_reason: Optional[str] = None

@router.post("/{doc_id}/review")
async def review_document(
    doc_id: str,
    payload: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 1. 查询公文和科室信息
    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404)
        
    # 【对齐修复】严格前置校验：仅提交态可审批
    if doc.status != DocumentStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail=f"公文当前状态为 {doc.status.value}，不可审批")
        
    res_dept = await db.execute(select(Department).where(Department.dept_id == doc.dept_id))
    dept = res_dept.scalars().first()
    
    # 2. 按优先级判定审批权限 (精准对齐基准)
    has_permission = False
    if dept and current_user.user_id == dept.dept_head_id:
        has_permission = True # 优先级 1：刚性负责人
    elif current_user.role_level >= 5 and current_user.dept_id == doc.dept_id:
        has_permission = True # 优先级 2：同科室科长
        
    if not has_permission:
        raise HTTPException(status_code=403, detail="审批权限不足：需为本科室负责人或科长")

    try:
        await DocumentService.review_document(db, doc_id, current_user.user_id, payload.is_approved, payload.rejection_reason)
        
        # 【对齐修复】注入实时通知推送
        from app.api.v1.endpoints.sse import notify_user
        msg_type = "APPROVAL_APPROVED" if payload.is_approved else "APPROVAL_REJECTED"
        await notify_user(doc.creator_id, msg_type, {
            "doc_id": doc_id,
            "title": doc.title,
            "reviewer": current_user.username,
            "reason": payload.rejection_reason
        })

        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
