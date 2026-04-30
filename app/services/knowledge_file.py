import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge import KnowledgePhysicalFile, SecurityLevel
from app.core.file_utils import calculate_hash, get_storage_path
from app.core.config import settings

class KnowledgeFileService:
    @staticmethod
    async def save_physical_file(
        db: AsyncSession, 
        file_content: bytes, 
        filename: str, 
        security_level: SecurityLevel
    ) -> tuple[int, bool]:
        """
        保存物理文件并去重。
        返回: (physical_file_id, needs_reparse)
        """
        content_hash = calculate_hash(file_content)
        
        # 1. 检查哈希是否存在
        stmt = select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == content_hash)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # 去重逻辑：若新安全等级更高，标记需重新解析
            needs_reparse = security_level.value > existing.security_level.value
            if needs_reparse:
                # 更新安全等级
                existing.security_level = security_level
                await db.commit()
            return existing.id, needs_reparse
        
        # 2. 存储到磁盘
        rel_path = get_storage_path(content_hash, filename)
        abs_path = os.path.join(settings.STORAGE_ROOT, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        with open(abs_path, "wb") as f:
            f.write(file_content)
        
        # 3. 记录到数据库
        new_phys = KnowledgePhysicalFile(
            file_path=rel_path,
            content_hash=content_hash,
            file_size=len(file_content),
            mime_type="application/octet-stream", 
            security_level=security_level
        )
        db.add(new_phys)
        await db.commit()
        await db.refresh(new_phys)
        
        return new_phys.id, True # 新文件始终需要解析
