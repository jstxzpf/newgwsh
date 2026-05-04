from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.models.system import NBSWorkflowAudit
from app.models.enums import WorkflowNodeId
from app.core.locks import acquire_redis_lock, release_redis_lock, extend_redis_lock
from app.core.exceptions import BusinessException
import uuid

class LockService:
    @staticmethod
    async def acquire_lock(db: AsyncSession, doc_id: str, user_id: int, username: str) -> str:
        result = await db.execute(select(Document).where(Document.doc_id == doc_id))
        doc = result.scalars().first()
        if not doc:
            raise BusinessException(404, "公文不存在")
        if doc.status != "DRAFTING":
            raise BusinessException(409, "公文已流转，不可编辑", "READONLY_IMMUTABLE")
        
        token = str(uuid.uuid4())
        success = await acquire_redis_lock(doc_id, user_id, username, token, ttl=180)
        if not success:
            raise BusinessException(423, "公文正在被他人编辑，当前只读", "READONLY_CONFLICT")
        return token

    @staticmethod
    async def heartbeat(doc_id: str, user_id: int, token: str) -> int:
        success = await extend_redis_lock(doc_id, user_id, token, ttl=180)
        if not success:
            raise BusinessException(403, "锁已失效或被夺", "LOCK_RECLAIMED")
        return 90 # next interval

    @staticmethod
    async def release_lock(db: AsyncSession, doc_id: str, user_id: int, token: str, content: str | None = None):
        if content is not None:
            # 容灾释放逻辑 (§二.3)：先存后放
            result = await db.execute(select(Document).where(Document.doc_id == doc_id))
            doc = result.scalars().first()
            if doc and doc.status == "DRAFTING":
                doc.content = content
                await db.commit()
                
        await release_redis_lock(doc_id, user_id, token)

    @staticmethod
    async def force_release(db: AsyncSession, doc_id: str, admin_id: int):
        # 强制释放锁并记录审计 (铁律 §二.3)
        await release_redis_lock(doc_id, user_id=0, token="", force=True) # 内部 force 逻辑
        
        audit = NBSWorkflowAudit(
            doc_id=doc_id,
            workflow_node_id=99, # 强制释放特殊代码
            operator_id=admin_id,
            action_details={"action": "FORCE_RELEASE_LOCK"}
        )
        db.add(audit)