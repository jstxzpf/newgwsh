from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_async_db
from app.models.document import WorkflowAudit
from typing import Optional
from datetime import datetime

from app.core.config import settings

router = APIRouter()

@router.get("/")
async def get_audit_logs(
    doc_id: Optional[str] = None,
    operator_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_async_db)
):
    stmt = select(WorkflowAudit)
    if doc_id:
        stmt = stmt.where(WorkflowAudit.doc_id == doc_id)
    if operator_id:
        stmt = stmt.where(WorkflowAudit.operator_id == operator_id)
    if start_time:
        stmt = stmt.where(WorkflowAudit.action_timestamp >= start_time)
        
    result = await db.execute(stmt.order_by(WorkflowAudit.action_timestamp.desc()).limit(settings.MAX_AUDIT_LOG_LIMIT))
    logs = result.scalars().all()
    return {"data": logs}
