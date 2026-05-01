from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.api import deps
from app.models.org import SystemUser
from app.models.audit import WorkflowAudit
from app.schemas.response import StandardResponse, success

router = APIRouter()

@router.get("/", response_model=StandardResponse)
async def list_audit_logs(
    doc_id: Optional[str] = None,
    operator_id: Optional[int] = None,
    node_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_active_user)
) -> Any:
    """安全审计大盘查询 (P8.1)"""
    # 权限校验: role_level >= 5 (科长及以上)
    if current_user.role_level < 5:
        return error(code=403, message="Insufficient permissions")
        
    stmt = select(WorkflowAudit)
    
    if doc_id:
        stmt = stmt.where(WorkflowAudit.doc_id == doc_id)
    if operator_id:
        stmt = stmt.where(WorkflowAudit.operator_id == operator_id)
    if node_id:
        stmt = stmt.where(WorkflowAudit.workflow_node_id == node_id)
        
    # 科长仅可查询本科室 (简便起见，这里假设审计记录中不直接存科室ID，需JOIN文档或用户)
    if current_user.role_level < 99:
        from app.models.document import Document
        stmt = stmt.join(Document).where(Document.dept_id == current_user.dept_id)

    stmt = stmt.order_by(desc(WorkflowAudit.action_timestamp))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(stmt)
    return success(data={"items": result.scalars().all(), "total": 0}) # total 简化
