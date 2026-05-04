from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.document import Document, DocumentSnapshot
from app.models.system import DocumentApprovalLog, NBSWorkflowAudit
from app.models.enums import DocumentStatus, WorkflowNodeId
from app.core.sip import generate_sip_hash
from app.core.exceptions import BusinessException
from app.core.locks import acquire_redis_lock, release_redis_lock
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
        # DIFF 保护逻辑矩阵 (依据后端设计方案 §二.2)
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
    async def submit_document(db: AsyncSession, doc: Document, user_id: int):
        # 铁律：前置状态校验 (§七.1)
        if doc.status != DocumentStatus.DRAFTING:
            raise BusinessException(409, "当前状态不可提交")
        
        # 逻辑：变更状态并释放锁
        doc.status = DocumentStatus.SUBMITTED
        
        log = DocumentApprovalLog(
            doc_id=doc.doc_id,
            submitter_id=user_id,
            decision_status="SUBMITTED",
            submitted_at=datetime.now(timezone.utc)
        )
        db.add(log)
        
        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id,
            workflow_node_id=WorkflowNodeId.SUBMITTED,
            operator_id=user_id
        )
        db.add(audit)
        # 注意：锁释放由调用方在 commit 后执行或通过 API 逻辑保证

    @staticmethod
    async def revise_document(db: AsyncSession, doc: Document, user_id: int, username: str) -> dict:
        # 铁律：原子性回退与抢锁顺序 (§七.1)
        if doc.status != DocumentStatus.REJECTED:
            raise BusinessException(409, "公文当前状态不允许回退修改")
        
        token = str(uuid.uuid4())
        # 原子抢锁
        success = await acquire_redis_lock(doc.doc_id, user_id, username, token, ttl=180)
        if not success:
            raise BusinessException(409, "锁已被抢占，无法回退")
        
        # 状态回退与清空建议稿
        doc.status = DocumentStatus.DRAFTING
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id,
            workflow_node_id=WorkflowNodeId.REVISION,
            operator_id=user_id
        )
        db.add(audit)
        
        return {
            "doc_id": doc.doc_id,
            "new_status": DocumentStatus.DRAFTING,
            "lock_acquired": True,
            "lock_token": token,
            "lock_expires_at": (datetime.now(timezone.utc).timestamp() + 180)
        }

    @staticmethod
    async def apply_polish(db: AsyncSession, doc: Document, final_content: str, user_id: int):
        # 铁律 (§四.1)：接受前备份快照
        snapshot = DocumentSnapshot(
            doc_id=doc.doc_id,
            content=doc.content,
            trigger_event="POLISH_APPLIED",
            creator_id=user_id
        )
        db.add(snapshot)
        
        doc.content = final_content
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id,
            workflow_node_id=WorkflowNodeId.POLISH_APPLIED,
            operator_id=user_id
        )
        db.add(audit)

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

    @staticmethod
    async def verify_sip(db: AsyncSession, doc_id: str) -> dict:
        # 获取该公文最新的已通过审批日志
        result = await db.execute(
            select(DocumentApprovalLog)
            .where(DocumentApprovalLog.doc_id == doc_id, DocumentApprovalLog.decision_status == "APPROVED")
            .order_by(DocumentApprovalLog.reviewed_at.desc())
        )
        log = result.scalars().first()
        if not log or not log.sip_hash:
            return {"match": False, "reason": "未找到有效的审批存证记录"}
        
        # 获取当前公文正文
        doc_result = await db.execute(select(Document).where(Document.doc_id == doc_id))
        doc = doc_result.scalars().first()
        if not doc:
            raise BusinessException(404, "公文不存在")
            
        # 重新执行归一化与哈希计算 (铁律 §六.6)
        # 必须使用存档时的 reviewer_id 和 reviewed_at
        current_hash = generate_sip_hash(
            doc.content or "", 
            log.reviewer_id, 
            log.reviewed_at.isoformat()
        )
        
        return {
            "match": current_hash == log.sip_hash,
            "stored_hash": log.sip_hash,
            "calculated_hash": current_hash,
            "reviewer_id": log.reviewer_id,
            "reviewed_at": log.reviewed_at
        }

    @staticmethod
    async def create_snapshot(db: AsyncSession, doc_id: str, content: str, user_id: int, event: str):
        snapshot = DocumentSnapshot(
            doc_id=doc_id,
            content=content,
            trigger_event=event,
            creator_id=user_id
        )
        db.add(snapshot)
        return snapshot.snapshot_id