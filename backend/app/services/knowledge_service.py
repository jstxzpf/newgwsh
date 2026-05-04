from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, text
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgePhysicalFile, KnowledgeChunk
from app.models.enums import KBTier, DataSecurityLevel
import hashlib
from datetime import datetime, timezone

class KnowledgeService:
    @staticmethod
    async def handle_upload(db: AsyncSession, filename: str, content: bytes, parent_id: int | None, kb_tier: KBTier, security_level: DataSecurityLevel, owner_id: int, dept_id: int | None) -> int:
        file_hash = hashlib.sha256(content).hexdigest()
        
        # 1. 物理去重检测 (依据实施约束 §一.2)
        result = await db.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == file_hash))
        phys_file = result.scalars().first()
        
        if not phys_file:
            phys_file = KnowledgePhysicalFile(content_hash=file_hash, file_path=f"/app/data/uploads/{file_hash}_{filename}", file_size=len(content))
            db.add(phys_file)
            await db.flush()
        else:
            # 2. 引用判断 (安全等级一致性校验)
            # 这里简化逻辑，暂假设如果等级不符则不复用 (实际应由解析任务决定是否重新切片)
            pass

        kb_node = KnowledgeBaseHierarchy(
            parent_id=parent_id,
            kb_name=filename,
            kb_type="FILE",
            kb_tier=kb_tier,
            dept_id=dept_id,
            security_level=security_level,
            parse_status="UPLOADED",
            physical_file_id=phys_file.file_id,
            owner_id=owner_id
        )
        db.add(kb_node)
        await db.flush()
        return kb_node.kb_id

    @staticmethod
    async def delete_node(db: AsyncSession, kb_id: int):
        # 铁律：级联软删除技术 (Recursive CTE Cleanup §三.2)
        # 获取所有子孙节点 ID
        cte_query = text("""
            WITH RECURSIVE subnodes AS (
                SELECT kb_id FROM knowledge_base_hierarchy WHERE kb_id = :kb_id
                UNION ALL
                SELECT h.kb_id FROM knowledge_base_hierarchy h
                INNER JOIN subnodes s ON h.parent_id = s.kb_id
            )
            SELECT kb_id FROM subnodes
        """)
        
        result = await db.execute(cte_query, {"kb_id": kb_id})
        target_ids = [row[0] for row in result.fetchall()]
        
        if not target_ids:
            return

        now = datetime.now(timezone.utc)
        
        # 1. 软删除目录树节点
        await db.execute(
            update(KnowledgeBaseHierarchy)
            .where(KnowledgeBaseHierarchy.kb_id.in_(target_ids))
            .values(is_deleted=True, deleted_at=now)
        )
        
        # 2. 软删除关联切片，并将 embedding 置 NULL (防幽灵检索)
        await db.execute(
            update(KnowledgeChunk)
            .where(KnowledgeChunk.kb_id.in_(target_ids))
            .values(is_deleted=True, embedding=None)
        )
        
        await db.commit()