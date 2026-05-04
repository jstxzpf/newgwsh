from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.document import Document, DocumentSnapshot
from app.models.system import DocumentApprovalLog, NBSWorkflowAudit
from app.models.enums import DocumentStatus, WorkflowNodeId
from app.core.sip import generate_sip_hash
from app.core.exceptions import BusinessException
import uuid
from datetime import datetime, timezone

class DocumentService:
    @staticmethod
    async def init_document(db: AsyncSession, title: str, doc_type_id: int, creator_id: int, dept_id: int | None) -> str:
        doc_id = str(uuid.uuid4())
        new_doc = Document(
            doc_id=doc_id,
            title=title,
            doc_type_id=doc_type_id,
            dept_id=dept_id,
            creator_id=creator_id,
            status=DocumentStatus.DRAFTING
        )
        db.add(new_doc)
        
        # 记录审计
        audit = NBSWorkflowAudit(
            doc_id=doc_id, workflow_node_id=WorkflowNodeId.DRAFTING,
            operator_id=creator_id
        )
        db.add(audit)
        return doc_id

    @staticmethod
    async def auto_save_draft(db: AsyncSession, doc: Document, title: str | None, content: str | None, draft_content: str | None):
        # DIFF 保护逻辑矩阵
        if doc.ai_polished_content:
            # DIFF 模式
            if content is not None:
                raise BusinessException(400, "DIFF 模式下禁止覆盖主正文")
            if draft_content is not None:
                doc.draft_suggestion = draft_content
        else:
            # SINGLE 模式
            if draft_content is not None:
                raise BusinessException(400, "SINGLE 模式下无需提交建议草稿")
            if content is not None:
                doc.content = content
                
        if title is not None:
            doc.title = title

    @staticmethod
    async def process_approval(db: AsyncSession, doc: Document, action: str, reviewer_id: int, comments: str | None):
        now = datetime.now(timezone.utc)
        
        if action == "APPROVE":
            doc.status = DocumentStatus.APPROVED
            sip = generate_sip_hash(doc.content or "", reviewer_id, now.isoformat())
            log = DocumentApprovalLog(
                doc_id=doc.doc_id, submitter_id=doc.creator_id, reviewer_id=reviewer_id,
                decision_status="APPROVED", sip_hash=sip, reviewed_at=now
            )
        elif action == "REJECT":
            if not comments:
                raise BusinessException(400, "驳回必须提供理由")
            doc.status = DocumentStatus.REJECTED
            log = DocumentApprovalLog(
                doc_id=doc.doc_id, submitter_id=doc.creator_id, reviewer_id=reviewer_id,
                decision_status="REJECTED", rejection_reason=comments, reviewed_at=now
            )
        else:
            raise BusinessException(400, "无效的审批动作")
            
        doc.reviewer_id = reviewer_id
        db.add(log)
        await db.flush()
        
        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id, workflow_node_id=WorkflowNodeId.APPROVED if action == "APPROVE" else WorkflowNodeId.REJECTED,
            operator_id=reviewer_id, reference_id=log.log_id,
            action_details={"reason": comments} if comments else {}
        )
        db.add(audit)
        return log.log_id