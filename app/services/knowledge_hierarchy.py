from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge import KnowledgeBaseHierarchy, KbType, KbTier, SecurityLevel
from typing import List, Optional

class KnowledgeHierarchyService:
    @staticmethod
    async def create_node(
        db: AsyncSession,
        kb_name: str,
        kb_type: KbType,
        kb_tier: KbTier,
        security_level: SecurityLevel,
        parent_id: Optional[int] = None,
        physical_file_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        dept_id: Optional[int] = None
    ) -> KnowledgeBaseHierarchy:
        node = KnowledgeBaseHierarchy(
            kb_name=kb_name,
            kb_type=kb_type,
            kb_tier=kb_tier,
            security_level=security_level,
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
    async def reuse_chunks(db: AsyncSession, source_kb_id: int, target_node: KnowledgeBaseHierarchy):
        """
        从源节点复制切片到目标节点 (切片复用契约)
        """
        from app.models.knowledge import KnowledgeChunk
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.kb_id == source_kb_id)
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        for c in chunks:
            new_chunk = KnowledgeChunk(
                kb_id=target_node.kb_id,
                physical_file_id=c.physical_file_id,
                content=c.content,
                embedding=c.embedding,
                metadata_json=c.metadata_json,
                # 冗余字段使用目标节点的数据
                is_deleted=False,
                kb_tier=target_node.kb_tier,
                security_level=target_node.security_level,
                dept_id=target_node.dept_id,
                owner_id=target_node.owner_id
            )
            db.add(new_chunk)
        
        target_node.parse_status = "READY"
        await db.commit()

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
                SELECT kb_id FROM knowledge_base_hierarchy WHERE kb_id = :root_id
                UNION ALL
                SELECT k.kb_id FROM knowledge_base_hierarchy k
                JOIN subtree s ON k.parent_id = s.kb_id
            )
            UPDATE knowledge_base_hierarchy
            SET is_deleted = True, updated_at = NOW()
            WHERE kb_id IN (SELECT kb_id FROM subtree)
        """)
        await db.execute(sql_hierarchy, {"root_id": root_id})
        
        # 2. 标记相关的向量切片并置空向量 (从索引移除防幽灵查出 P4.2)
        sql_chunks = text("""
            UPDATE knowledge_chunks
            SET is_deleted = True, embedding = NULL, updated_at = NOW()
            WHERE kb_id IN (
                WITH RECURSIVE subtree AS (
                    SELECT kb_id FROM knowledge_base_hierarchy WHERE kb_id = :root_id
                    UNION ALL
                    SELECT k.kb_id FROM knowledge_base_hierarchy k
                    JOIN subtree s ON k.parent_id = s.kb_id
                )
                SELECT kb_id FROM subtree
            )
        """)
        await db.execute(sql_chunks, {"root_id": root_id})
        
        await db.commit()
