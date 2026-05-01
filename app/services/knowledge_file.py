import os
from typing import Optional
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
    ) -> tuple[int, Optional[int]]:
        """
        保存物理文件并去重。
        返回: (physical_file_id, existing_kb_id_for_reuse)
        """
        content_hash = calculate_hash(file_content)
        
        # 1. 检查物理文件是否存在
        stmt_phys = select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == content_hash)
        phys = (await db.execute(stmt_phys)).scalar_one_or_none()
        
        if not phys:
            # 存储到磁盘
            rel_path = get_storage_path(content_hash, filename)
            abs_path = os.path.join(settings.STORAGE_ROOT, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "wb") as f:
                f.write(file_content)
            
            phys = KnowledgePhysicalFile(
                file_path=rel_path,
                content_hash=content_hash,
                file_size=len(file_content),
                mime_type="application/octet-stream"
            )
            db.add(phys)
            await db.commit()
            await db.refresh(phys)
        
        # 2. 检查是否有【等级一致】且【已就绪】的逻辑节点可供复用
        # 根据《实施约束规则》: 等级不一致(升级或降级)均严禁复用
        from app.models.knowledge import KnowledgeBaseHierarchy
        stmt_node = select(KnowledgeBaseHierarchy).where(
            KnowledgeBaseHierarchy.physical_file_id == phys.file_id,
            KnowledgeBaseHierarchy.security_level == security_level,
            KnowledgeBaseHierarchy.parse_status == "READY",
            KnowledgeBaseHierarchy.is_deleted == False
        ).limit(1)
        existing_node = (await db.execute(stmt_node)).scalar_one_or_none()
        
        return phys.file_id, existing_node.kb_id if existing_node else None
