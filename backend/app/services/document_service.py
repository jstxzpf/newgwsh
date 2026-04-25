import hashlib
import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.document import Document, DocumentSnapshot, DocumentApprovalLog, WorkflowAudit
from app.core.enums import DocumentStatus, WorkflowNode
from app.services.sip_service import SIPService
from app.core.redis import redis_client
from datetime import datetime
import json

class DocumentService:
    @staticmethod
    async def get_document(db: AsyncSession, doc_id: str) -> Optional[Document]:
        result = await db.execute(select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False))
        return result.scalars().first()

    @staticmethod
    async def init_document(db: AsyncSession, title: str, user_id: int, dept_id: int):
        doc_id = str(uuid.uuid4())
        
        doc = Document(
            doc_id=doc_id,
            title=title,
            creator_id=user_id,
            dept_id=dept_id,
            status=DocumentStatus.DRAFTING
        )
        db.add(doc)
        
        audit = WorkflowAudit(
            doc_id=doc_id,
            workflow_node_id=WorkflowNode.DRAFTING,
            operator_id=user_id,
            action_details={"note": "初始化起草公文"}
        )
        db.add(audit)
        
        await db.commit()
        return doc_id

    @staticmethod
    async def auto_save(
        db: AsyncSession, 
        doc_id: str, 
        content: Optional[str] = None, 
        draft_content: Optional[str] = None,
        has_content_key: bool = False
    ) -> Tuple[Optional[Document], bool]:
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            return None, False
        
        # 严格防御：若处于 DIFF 模式（ai_polished_content 非空），则必须拒绝包含 content 键的请求
        if doc.ai_polished_content is not None and has_content_key:
            raise ValueError("Forbidden: Cannot overwrite main content while in DIFF mode. Use draft_content only.")

        changed = False
        if draft_content is not None:
            if doc.draft_suggestion != draft_content:
                doc.draft_suggestion = draft_content
                changed = True
        elif content is not None:
            if content != doc.content:
                doc.content = content
                changed = True
        
        if changed:
            await db.commit()
        return doc, changed

    @staticmethod
    async def submit_document(db: AsyncSession, doc_id: str, user_id: int):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise ValueError("Document not found")
            
        if doc.status != DocumentStatus.DRAFTING and doc.status != DocumentStatus.REJECTED:
            raise ValueError("Only DRAFTING or REJECTED documents can be submitted")
            
        # 1. 锁与归属权判定 (严格对齐文档)
        lock_key = f"lock:{doc_id}"
        current_lock = await redis_client.get(lock_key)
        
        if current_lock:
            lock_data = json.loads(current_lock)
            if lock_data.get("user_id") != user_id:
                # 锁存在且不属于当前提交者，抛出 409
                raise RuntimeError("409 Conflict: Lock is held by another user. Cannot submit.")
            else:
                # 锁存在且属于当前提交者，予以放行并主动销毁
                await redis_client.delete(lock_key)
        else:
            # 如果锁不存在（可能过期），则校验当前提交者必须是该公文的起草人
            if doc.creator_id != user_id:
                raise PermissionError("403 Forbidden: Only the creator can submit an unlocked document.")
            
        # 2. 状态迁转
        doc.status = DocumentStatus.SUBMITTED
        
        audit = WorkflowAudit(
            doc_id=doc_id,
            workflow_node_id=WorkflowNode.SUBMITTED,
            operator_id=user_id,
            action_details={"note": "起草人提交审批"}
        )
        db.add(audit)
        
        await db.commit()
        return doc

    @staticmethod
    async def apply_polish(db: AsyncSession, doc_id: str, user_id: int, final_content: Optional[str] = None):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise ValueError("Document not found")
        
        snapshot = DocumentSnapshot(
            doc_id=doc_id,
            content=doc.content,
            trigger_event="accept_polish",
            creator_id=user_id
        )
        db.add(snapshot)
        
        content_to_apply = final_content if final_content is not None else doc.ai_polished_content
        if not content_to_apply:
            raise ValueError("No polished content to apply")
            
        action_details = {}
        if final_content is not None and final_content != doc.ai_polished_content:
            action_details["note"] = "用户接受并修改后应用"
        else:
            action_details["note"] = "用户全盘接受 AI 建议"
            
        audit = WorkflowAudit(
            doc_id=doc_id,
            workflow_node_id=WorkflowNode.POLISH,
            operator_id=user_id,
            action_details=action_details
        )
        db.add(audit)
        
        doc.content = content_to_apply
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        await db.commit()
        return doc

    @staticmethod
    async def discard_polish(db: AsyncSession, doc_id: str):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise ValueError("Document not found")
        
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        await db.commit()
        return doc

    @staticmethod
    async def review_document(
        db: AsyncSession, 
        doc_id: str, 
        reviewer_id: int, 
        is_approved: bool, 
        rejection_reason: str = None
    ):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc or doc.status != DocumentStatus.SUBMITTED:
            raise ValueError("Document not found or not in SUBMITTED state")
            
        now = datetime.now()
        doc.reviewer_id = reviewer_id
        
        audit_node = WorkflowNode.APPROVED if is_approved else WorkflowNode.REJECTED
        new_status = DocumentStatus.APPROVED if is_approved else DocumentStatus.REJECTED
        
        sip_hash = None
        if is_approved:
            sip_hash = SIPService.generate_sip_fingerprint(doc.content, reviewer_id, now)
        else:
            if not rejection_reason:
                raise ValueError("Rejection reason is required")
                
        doc.status = new_status
        
        approval_log = DocumentApprovalLog(
            doc_id=doc_id,
            submitter_id=doc.creator_id,
            reviewer_id=reviewer_id,
            decision_status=new_status.value,
            rejection_reason=rejection_reason,
            sip_hash=sip_hash,
            reviewed_at=now
        )
        db.add(approval_log)
        
        audit = WorkflowAudit(
            doc_id=doc_id,
            workflow_node_id=audit_node,
            operator_id=reviewer_id,
            action_details={"rejection_reason": rejection_reason} if not is_approved else {"sip_generated": bool(sip_hash)}
        )
        db.add(audit)
        
        await db.commit()
        return doc

    @staticmethod
    async def revise_document(db: AsyncSession, doc_id: str, user_id: int, username: str):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc or doc.status != DocumentStatus.REJECTED:
            raise ValueError("Only REJECTED documents can be revised")
            
        doc.status = DocumentStatus.DRAFTING
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        audit = WorkflowAudit(
            doc_id=doc_id,
            workflow_node_id=WorkflowNode.REVISION,
            operator_id=user_id,
            action_details={"note": "起草人开始驳回修改"}
        )
        db.add(audit)
        
        # Redis NX 原子抢锁
        lock_key = f"lock:{doc_id}"
        token = str(uuid.uuid4())
        lock_data = {
            "user_id": user_id,
            "username": username,
            "acquired_at": datetime.now().isoformat(),
            "token": token
        }
        from app.core.config import settings
        success = await redis_client.set(
            lock_key, 
            json.dumps(lock_data), 
            nx=True, 
            ex=settings.LOCK_TTL_SECONDS
        )
        
        if not success:
            raise ValueError("Failed to acquire lock. It might be held by another session.")
            
        await db.commit()
        
        return {
            "doc_id": doc_id,
            "new_status": "DRAFTING",
            "lock_acquired": True,
            "lock_token": token,
            "lock_expires_at": (datetime.now().timestamp() + settings.LOCK_TTL_SECONDS)
        }
