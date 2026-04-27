from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import WorkflowAudit
from app.core.database import AsyncSessionLocal
from app.core.enums import WorkflowNode
from typing import Any, Dict

class AuditService:
    @staticmethod
    async def write_audit_log(
        doc_id: str, 
        workflow_node: WorkflowNode, 
        operator_id: int, 
        action_details: Dict[str, Any] = None,
        db: AsyncSession = None
    ):
        if db is None:
            async with AsyncSessionLocal() as session:
                await AuditService._perform_write(session, doc_id, workflow_node, operator_id, action_details)
        else:
            await AuditService._perform_write(db, doc_id, workflow_node, operator_id, action_details)

    @staticmethod
    async def _perform_write(
        db: AsyncSession,
        doc_id: str,
        workflow_node: WorkflowNode,
        operator_id: int,
        action_details: Dict[str, Any]
    ):
        audit = WorkflowAudit(
            doc_id=doc_id,
            workflow_node_id=workflow_node,
            operator_id=operator_id,
            action_details=action_details or {}
        )
        db.add(audit)
        await db.commit()
