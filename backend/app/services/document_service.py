import hashlib
import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.document import Document, DocumentSnapshot, DocumentApprovalLog, WorkflowAudit
from app.core.enums import DocumentStatus, WorkflowNode
from app.services.sip_service import SIPService
from app.core.redis import redis_client, get_redis
from datetime import datetime
import json
from app.core.exceptions import DocumentLockedError, DocumentPermissionError, DocumentStateError

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
        await db.commit()
        return doc_id

    @staticmethod
    def _calculate_content_hash(content: str) -> str:
        if not content:
            return ""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

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
            raise DocumentStateError("Forbidden: Cannot overwrite main content while in DIFF mode. Use draft_content only.")

        changed = False
        if doc.ai_polished_content is not None:
             # DIFF 模式：仅更新草稿建议 (使用哈希对比对齐审计)
             if draft_content is not None:
                 old_hash = DocumentService._calculate_content_hash(doc.draft_suggestion)
                 new_hash = DocumentService._calculate_content_hash(draft_content)
                 if old_hash != new_hash:
                     doc.draft_suggestion = draft_content
                     changed = True
        else:
             # 常规模式：更新正文 (使用哈希对比对齐审计)
             if content is not None:
                 old_hash = DocumentService._calculate_content_hash(doc.content)
                 new_hash = DocumentService._calculate_content_hash(content)
                 if old_hash != new_hash:
                     doc.content = content
                     changed = True
        
        if changed:
            await db.commit()
        return doc, changed

    @staticmethod
    async def submit_document(db: AsyncSession, doc_id: str, user_id: int):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise DocumentStateError("Document not found")
            
        # 【对齐修复】严格状态机网关校验
        if doc.status not in [DocumentStatus.DRAFTING, DocumentStatus.REJECTED]:
            raise DocumentStateError(
                f"Cannot submit document in '{doc.status.value}' state. "
                f"Only DRAFTING or REJECTED documents can be submitted."
            )
            
        # 0. 业务校验：标题与正文
        if not doc.title or doc.title == "新公文草稿" or doc.title == "未命名公文":
            raise DocumentStateError("提交审批前必须填写正式公文标题")
        if not doc.content or len(doc.content.strip()) < 10:
            raise DocumentStateError("公文正文过短，无法提交审批")

        # 1. 锁与归属权判定 (严格对齐文档)
        lock_key = f"lock:{doc_id}"
        redis_client = await get_redis()
        current_lock = await redis_client.get(lock_key)
        
        tolerance_flag = False
        if current_lock:
            lock_data = json.loads(current_lock)
            if lock_data.get("user_id") != user_id:
                # 锁存在且不属于当前提交者
                raise DocumentLockedError("Lock is held by another user. Cannot submit.")
            else:
                # 锁存在且属于当前提交者，予以放行并主动销毁
                await redis_client.delete(lock_key)
        else:
            # 如果锁不存在（可能过期），则校验当前提交者必须是该公文的起草人
            if doc.creator_id != user_id:
                raise DocumentPermissionError("Only the creator can submit an unlocked document.")
            tolerance_flag = True # 标记为锁过期容忍
            
        # 2. 状态迁转
        doc.status = DocumentStatus.SUBMITTED
        await db.commit()
        return doc, tolerance_flag

    @staticmethod
    async def apply_polish(db: AsyncSession, doc_id: str, user_id: int, final_content: Optional[str] = None):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise DocumentStateError("Document not found")
        
        content_to_apply = final_content if final_content is not None else doc.ai_polished_content
        if not content_to_apply:
            raise DocumentStateError("No polished content to apply")

        # 【对齐修复】内容一致性校验：无变更则跳过快照生成
        if content_to_apply == doc.content:
            doc.ai_polished_content = None
            doc.draft_suggestion = None
            await db.commit()
            return doc

        snapshot = DocumentSnapshot(
            doc_id=doc_id,
            content=doc.content,
            trigger_event="accept_polish",
            creator_id=user_id
        )
        db.add(snapshot)
        
        doc.content = content_to_apply
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        await db.commit()
        return doc

    @staticmethod
    async def discard_polish(db: AsyncSession, doc_id: str):
        # 【对齐修复】补全逻辑：清空润色建议及草稿建议，退出 DIFF 模式
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise DocumentStateError("Document not found")
        
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
            raise DocumentStateError("Document not found or not in SUBMITTED state")
            
        now = datetime.now().replace(microsecond=0) # 【对齐修复】确保存储与指纹计算精度一致
        
        new_status = DocumentStatus.APPROVED if is_approved else DocumentStatus.REJECTED
        
        sip_hash = None
        if is_approved:
            sip_hash = SIPService.generate_sip_fingerprint(doc.content, reviewer_id, now)
        else:
            if not rejection_reason:
                raise DocumentStateError("Rejection reason is required")
                
        # 【对齐修复】确保 reviewer_id 更新与日志写入在同一原子事务内
        doc.reviewer_id = reviewer_id
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
        await db.commit()
        return doc

    @staticmethod
    async def list_documents(
        db: AsyncSession, 
        user_id: int, 
        dept_id: int, 
        role_level: int,
        status: Optional[DocumentStatus] = None,
        page: int = 1,
        page_size: int = 20
    ):
        from sqlalchemy import or_
        stmt = select(Document).where(Document.is_deleted == False)
        
        # 三层权限隔离
        if role_level >= 99: # 超级管理员
            pass
        elif role_level >= 5: # 科长，可看本科室所有
            stmt = stmt.where(Document.dept_id == dept_id)
        else: # 普通科员
            # 【对齐修复】可见：本人的全部公文 + 本科室其他人的非草稿公文
            stmt = stmt.where(
                or_(
                    Document.creator_id == user_id,
                    (Document.dept_id == dept_id) & (Document.status != DocumentStatus.DRAFTING)
                )
            )
            
        if status:
            stmt = stmt.where(Document.status == status)
            
        stmt = stmt.order_by(Document.updated_at.desc()).offset((page-1)*page_size).limit(page_size)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def revise_document(db: AsyncSession, doc_id: str, user_id: int, username: str):
        # 【对齐修复】使用 FOR UPDATE 行级锁防止并发修改竞态
        stmt = select(Document).where(
            Document.doc_id == doc_id, 
            Document.is_deleted == False
        ).with_for_update()
        res = await db.execute(stmt)
        doc = res.scalars().first()

        if not doc or doc.status != DocumentStatus.REJECTED:
            raise DocumentStateError("Only REJECTED documents can be revised")
            
        # 1. 【原子抢锁增强】必须在任何数据库写操作之前
        lock_key = f"lock:{doc_id}"
        token = str(uuid.uuid4())
        redis_client = await get_redis()
        
        lock_data = {
            "user_id": user_id,
            "username": username,
            "acquired_at": datetime.now().isoformat(),
            "token": token
        }
        lock_val = json.dumps(lock_data)
        from app.core.config import settings
        
        # 尝试直接抢锁 (NX = Not Exist)
        success = await redis_client.set(lock_key, lock_val, nx=True, ex=settings.LOCK_TTL_SECONDS)
        
        if not success:
            # 抢锁失败，检查是否是本人的残留锁
            current_raw = await redis_client.get(lock_key)
            if current_raw:
                try:
                    current_data = json.loads(current_raw)
                    if current_data.get("user_id") != user_id:
                         raise DocumentLockedError("该公文正被他人锁定修改中，无法唤醒")
                    else:
                         # 是本人的锁，直接覆盖更新 (容错处理)
                         await redis_client.set(lock_key, lock_val, ex=settings.LOCK_TTL_SECONDS)
                         success = True
                except json.JSONDecodeError:
                    await redis_client.delete(lock_key)
                    success = await redis_client.set(lock_key, lock_val, nx=True, ex=settings.LOCK_TTL_SECONDS)
        
        if not success:
            raise DocumentLockedError("无法获取公文编辑锁")
            
        try:
            doc.status = DocumentStatus.DRAFTING
            doc.ai_polished_content = None
            doc.draft_suggestion = None
            await db.commit()
        except Exception:
            await redis_client.delete(lock_key) # 数据库失败则释放锁
            raise
        
        return {
            "doc_id": doc_id,
            "new_status": "DRAFTING",
            "lock_acquired": True,
            "lock_token": token,
            "lock_expires_at": (datetime.now().timestamp() + settings.LOCK_TTL_SECONDS)
        }
