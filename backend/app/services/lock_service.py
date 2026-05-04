from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
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
            result = await db.execute(select(Document).where(Document.doc_id == doc_id))
            doc = result.scalars().first()
            if doc and doc.status == "DRAFTING":
                doc.content = content
                await db.commit()
                
        await release_redis_lock(doc_id, user_id, token)