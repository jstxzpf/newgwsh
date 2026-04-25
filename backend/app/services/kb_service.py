import os
import hashlib
import aiofiles
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from fastapi import UploadFile
from app.models.knowledge import KnowledgePhysicalFile, KnowledgeBaseHierarchy
from app.core.enums import KBTier, DataSecurityLevel

UPLOAD_DIR = os.path.join(os.getcwd(), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class KBService:
    @staticmethod
    async def get_or_create_physical_file(db: AsyncSession, file: UploadFile) -> KnowledgePhysicalFile:
        # 计算文件 Hash
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        await file.seek(0) # 重置游标

        result = await db.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == file_hash))
        existing_file = result.scalars().first()
        
        if existing_file:
            return existing_file
            
        # 落盘物理文件
        file_ext = os.path.splitext(file.filename)[1]
        phys_path = os.path.join(UPLOAD_DIR, f"{file_hash}{file_ext}")
        
        async with aiofiles.open(phys_path, 'wb') as f:
            await f.write(content)
            
        new_phys = KnowledgePhysicalFile(
            content_hash=file_hash,
            file_path=phys_path,
            file_size=len(content)
        )
        db.add(new_phys)
        await db.commit()
        await db.refresh(new_phys)
        return new_phys

    @staticmethod
    async def create_hierarchy_node(
        db: AsyncSession, 
        filename: str, 
        phys_id: int, 
        user_id: int,
        kb_tier: KBTier = KBTier.PERSONAL,
        security_level: DataSecurityLevel = DataSecurityLevel.GENERAL
    ) -> KnowledgeBaseHierarchy:
        node = KnowledgeBaseHierarchy(
            kb_name=filename,
            kb_type="FILE",
            kb_tier=kb_tier,
            security_level=security_level,
            parse_status="UPLOADED",
            physical_file_id=phys_id,
            owner_id=user_id
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    @staticmethod
    async def delete_kb_node(db: AsyncSession, kb_id: int):
        """
        利用 WITH RECURSIVE CTE 找出所有下级，执行双重级联软删除，并剥离向量
        """
        # 1. 软删目录树
        sql = """
        WITH RECURSIVE target_nodes AS (
            SELECT kb_id FROM knowledge_base_hierarchy WHERE kb_id = :kb_id
            UNION ALL
            SELECT h.kb_id FROM knowledge_base_hierarchy h
            INNER JOIN target_nodes t ON h.parent_id = t.kb_id
        )
        UPDATE knowledge_base_hierarchy 
        SET is_deleted = TRUE, deleted_at = NOW() 
        WHERE kb_id IN (SELECT kb_id FROM target_nodes);
        """
        await db.execute(text(sql), {"kb_id": kb_id})
        
        # 2. 同步软删切片，并将其向量置空以防幽灵检索（双重保险）
        chunk_sql = """
        WITH RECURSIVE target_nodes AS (
            SELECT kb_id FROM knowledge_base_hierarchy WHERE kb_id = :kb_id
            UNION ALL
            SELECT h.kb_id FROM knowledge_base_hierarchy h
            INNER JOIN target_nodes t ON h.parent_id = t.kb_id
        )
        UPDATE knowledge_chunks 
        SET is_deleted = TRUE, embedding = NULL 
        WHERE kb_id IN (SELECT kb_id FROM target_nodes);
        """
        await db.execute(text(chunk_sql), {"kb_id": kb_id})
        await db.commit()
