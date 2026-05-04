from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgePhysicalFile
from app.models.enums import KBTier, DataSecurityLevel
import hashlib

class KnowledgeService:
    @staticmethod
    async def handle_upload(db: AsyncSession, filename: str, content: bytes, parent_id: int | None, kb_tier: KBTier, security_level: DataSecurityLevel, owner_id: int, dept_id: int | None) -> int:
        file_hash = hashlib.sha256(content).hexdigest()
        
        # 检查物理去重
        result = await db.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == file_hash))
        phys_file = result.scalars().first()
        
        if not phys_file:
            # 模拟写文件到磁盘逻辑
            phys_file = KnowledgePhysicalFile(content_hash=file_hash, file_path=f"/app/data/uploads/{file_hash}_{filename}", file_size=len(content))
            db.add(phys_file)
            await db.flush()
            
        kb_node = KnowledgeBaseHierarchy(
            parent_id=parent_id,
            kb_name=filename,
            kb_type="FILE",
            kb_tier=kb_tier,
            dept_id=dept_id,
            security_level=security_level,
            parse_status="READY" if phys_file.file_size else "UPLOADED",
            physical_file_id=phys_file.file_id,
            owner_id=owner_id
        )
        db.add(kb_node)
        await db.flush()
        return kb_node.kb_id