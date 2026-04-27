import os
import hashlib
import aiofiles
from typing import Optional
from datetime import datetime
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
        dept_id: Optional[int] = None,
        kb_tier: KBTier = KBTier.PERSONAL,
        security_level: DataSecurityLevel = DataSecurityLevel.GENERAL,
        parent_id: Optional[int] = None
    ) -> KnowledgeBaseHierarchy:
        node = KnowledgeBaseHierarchy(
            kb_name=filename,
            kb_type="FILE",
            kb_tier=kb_tier,
            security_level=security_level,
            dept_id=dept_id,
            parse_status="UPLOADED",
            physical_file_id=phys_id,
            owner_id=user_id,
            parent_id=parent_id
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    @staticmethod
    async def replace_kb_node(
        db: AsyncSession,
        kb_id: int,
        filename: str,
        phys_id: int,
        user_id: int
    ):
        stmt = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == kb_id)
        result = await db.execute(stmt)
        node = result.scalars().first()
        if not node:
            return None
            
        # 更新节点信息
        node.kb_name = filename
        node.physical_file_id = phys_id
        node.parse_status = "PARSING"
        node.file_version += 1 # 【对齐修复】版本自增
        node.updated_at = datetime.now()
        
        # 联动清理旧的切片（防止幽灵检索）
        chunk_sql = "UPDATE knowledge_chunks SET is_deleted = TRUE, embedding = NULL WHERE kb_id = :kb_id"
        await db.execute(text(chunk_sql), {"kb_id": kb_id})
        
        await db.commit()
        return node

    @staticmethod
    async def get_or_create_directory(
        db: AsyncSession,
        name: str,
        parent_id: Optional[int],
        user_id: int,
        dept_id: Optional[int],
        kb_tier: KBTier
    ) -> KnowledgeBaseHierarchy:
        stmt = select(KnowledgeBaseHierarchy).where(
            KnowledgeBaseHierarchy.kb_name == name,
            KnowledgeBaseHierarchy.parent_id == parent_id,
            KnowledgeBaseHierarchy.kb_type == "DIRECTORY",
            KnowledgeBaseHierarchy.is_deleted == False
        )
        result = await db.execute(stmt)
        directory = result.scalars().first()
        
        if not directory:
            directory = KnowledgeBaseHierarchy(
                kb_name=name,
                kb_type="DIRECTORY",
                kb_tier=kb_tier,
                dept_id=dept_id,
                owner_id=user_id,
                parent_id=parent_id,
                parse_status="READY" # 目录无需解析
            )
            db.add(directory)
            await db.commit()
            await db.refresh(directory)
            
        return directory

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
