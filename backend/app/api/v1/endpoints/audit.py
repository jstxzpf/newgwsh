from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_async_db
from app.models.document import WorkflowAudit
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_audit_logs(
    doc_id: Optional[str] = None,
    operator_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db)
):
    stmt = select(WorkflowAudit)
    if doc_id:
        stmt = stmt.where(WorkflowAudit.doc_id == doc_id)
    if operator_id:
        stmt = stmt.where(WorkflowAudit.operator_id == operator_id)
        
    result = await db.execute(stmt.order_by(WorkflowAudit.action_timestamp.desc()).limit(50))
    logs = result.scalars().all()
    return {"data": logs}
