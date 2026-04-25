import hashlib
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.document import Document, DocumentSnapshot
from app.core.enums import DocumentStatus

class DocumentService:
    @staticmethod
    async def get_document(db: AsyncSession, doc_id: str) -> Optional[Document]:
        result = await db.execute(select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False))
        return result.scalars().first()

    @staticmethod
    async def auto_save(
        db: AsyncSession, 
        doc_id: str, 
        content: Optional[str] = None, 
        draft_content: Optional[str] = None
    ):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            return None
        
        # 校验 DIFF 模式保护：若处于润色态，拒绝直接覆写 content
        if doc.ai_polished_content and content is not None:
            raise ValueError("Cannot overwrite main content while in DIFF mode. Use draft_content instead.")

        if draft_content is not None:
            doc.draft_suggestion = draft_content
        elif content is not None:
            # 计算哈希判重
            if content != doc.content:
                doc.content = content
        
        await db.commit()
        return doc

    @staticmethod
    async def apply_polish(db: AsyncSession, doc_id: str, user_id: int, final_content: Optional[str] = None):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise ValueError("Document not found")
        
        # 1. 生成快照备份原值
        snapshot = DocumentSnapshot(
            doc_id=doc_id,
            content=doc.content,
            trigger_event="accept_polish",
            creator_id=user_id
        )
        db.add(snapshot)
        
        # 2. 覆盖正文
        content_to_apply = final_content if final_content is not None else doc.ai_polished_content
        if not content_to_apply:
            raise ValueError("No polished content to apply")
        
        doc.content = content_to_apply
        
        # 3. 清空 DIFF 状态缓存
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        await db.commit()
        return doc

    @staticmethod
    async def discard_polish(db: AsyncSession, doc_id: str):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise ValueError("Document not found")
        
        # 清空 DIFF 状态缓存
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        await db.commit()
        return doc
