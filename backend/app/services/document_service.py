import hashlib
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.document import Document
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
            # 简单比较（实际可更复杂）
            if content != doc.content:
                doc.content = content
        
        await db.commit()
        return doc
