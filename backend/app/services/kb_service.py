import os
import hashlib
import aiofiles
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
