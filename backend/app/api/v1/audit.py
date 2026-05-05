from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.system import NBSWorkflowAudit
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("")
async def list_audit_logs(
    doc_id: str | None = None,
    operator_id: int | None = None,
    node_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 权限校验：负责人及以上 (§10)
    if current_user.role_level < 5:
        raise BusinessException(403, "无权查看审计日志")

    query = select(NBSWorkflowAudit).where(NBSWorkflowAudit.audit_id > 0)
    
    # 权限隔离：科长仅见本科室 (§10)
    if current_user.role_level < 99:
        from app.models.document import Document
        query = query.join(Document, Document.doc_id == NBSWorkflowAudit.doc_id).where(Document.dept_id == current_user.dept_id)

    if doc_id:
        query = query.where(NBSWorkflowAudit.doc_id == doc_id)
    if operator_id:
        query = query.where(NBSWorkflowAudit.operator_id == operator_id)
    if node_id:
        query = query.where(NBSWorkflowAudit.workflow_node_id == node_id)

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query.order_by(NBSWorkflowAudit.action_timestamp.desc()).offset((page-1)*page_size).limit(page_size))
    items = result.scalars().all()
    
    return {"code": 200, "message": "success", "data": {
        "total": total,
        "items": [
            {
                "audit_id": i.audit_id,
                "doc_id": i.doc_id,
                "node_id": i.workflow_node_id,
                "operator_id": i.operator_id,
                "details": i.action_details,
                "timestamp": i.action_timestamp
            } for i in items
        ]
    }}

from app.core.exceptions import BusinessException