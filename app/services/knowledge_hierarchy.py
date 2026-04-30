from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge import KnowledgeBaseHierarchy, KbType, KbTier
from typing import List, Optional

class KnowledgeHierarchyService:
    @staticmethod
    async def create_node(
        db: AsyncSession,
        name: str,
        kb_type: KbType,
        kb_tier: KbTier,
        parent_id: Optional[int] = None,
        physical_file_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        dept_id: Optional[int] = None
    ) -> KnowledgeBaseHierarchy:
        node = KnowledgeBaseHierarchy(
            name=name,
            kb_type=kb_type,
            kb_tier=kb_tier,
            parent_id=parent_id,
            physical_file_id=physical_file_id,
            owner_id=owner_id,
            dept_id=dept_id
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    @staticmethod
    async def get_nodes(
        db: AsyncSession,
        kb_tier: Optional[KbTier] = None,
        parent_id: Optional[int] = None,
        is_deleted: bool = False
    ) -> List[KnowledgeBaseHierarchy]:
        stmt = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == is_deleted)
        if kb_tier:
            stmt = stmt.where(KnowledgeBaseHierarchy.kb_tier == kb_tier)
        if parent_id:
            stmt = stmt.where(KnowledgeBaseHierarchy.parent_id == parent_id)
        else:
            stmt = stmt.where(KnowledgeBaseHierarchy.parent_id == None)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def soft_delete_subtree(db: AsyncSession, root_id: int):
        """
        递归软删除整个子树及相关的向量分片。
        """
        # 1. 标记层级树
        sql_hierarchy = text("""
            WITH RECURSIVE subtree AS (
                SELECT id FROM knowledge_base_hierarchy WHERE id = :root_id
                UNION ALL
                SELECT k.id FROM knowledge_base_hierarchy k
                JOIN subtree s ON k.parent_id = s.id
            )
            UPDATE knowledge_base_hierarchy
            SET is_deleted = True, updated_at = NOW()
            WHERE id IN (SELECT id FROM subtree)
        """)
        await db.execute(sql_hierarchy, {"root_id": root_id})
        
        # 2. 标记相关的向量切片
        sql_chunks = text("""
            UPDATE knowledge_chunks
            SET is_deleted = True, updated_at = NOW()
            WHERE kb_id IN (
                WITH RECURSIVE subtree AS (
                    SELECT id FROM knowledge_base_hierarchy WHERE id = :root_id
                    UNION ALL
                    SELECT k.id FROM knowledge_base_hierarchy k
                    JOIN subtree s ON k.parent_id = s.id
                )
                SELECT id FROM subtree
            )
        """)
        await db.execute(sql_chunks, {"root_id": root_id})
        
        await db.commit()
