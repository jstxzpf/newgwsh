from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk, KnowledgePhysicalFile
from app.models.system import NBSWorkflowAudit
from app.models.enums import WorkflowNodeId, KBTypeEnum, KBTier, DataSecurityLevel
from datetime import datetime, timezone
import hashlib
import os

class KnowledgeService:
    @staticmethod
    async def handle_upload(
        db: AsyncSession,
        filename: str,
        content: bytes,
        parent_id: int | None,
        kb_tier: KBTier,
        security_level: DataSecurityLevel,
        user_id: int,
        dept_id: int | None
    ) -> tuple[int, bool]:
        """Returns (kb_id, needs_parse)."""
        # 1. 物理去重预检 (Task 4 §三.5)
        content_hash = hashlib.sha256(content).hexdigest()

        result = await db.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == content_hash))
        physical_file = result.scalars().first()

        if not physical_file:
            file_path = f"/app/data/uploads/{content_hash}_{filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)
            physical_file = KnowledgePhysicalFile(
                content_hash=content_hash,
                file_path=file_path,
                file_size=len(content)
            )
            db.add(physical_file)
            await db.flush()

        # 2. 逻辑去重检查 (§三.5)
        # 允许安全等级升级：同名同层文件若等级不同则更新等级并强制重新解析
        existing_node_query = select(KnowledgeBaseHierarchy).where(
            KnowledgeBaseHierarchy.physical_file_id == physical_file.file_id,
            KnowledgeBaseHierarchy.owner_id == user_id,
            KnowledgeBaseHierarchy.kb_tier == kb_tier,
            KnowledgeBaseHierarchy.is_deleted == False
        )
        existing_node = (await db.execute(existing_node_query)).scalars().first()
        if existing_node:
            if existing_node.security_level != security_level:
                existing_node.security_level = security_level
                existing_node.parse_status = "UPLOADED"
                return existing_node.kb_id, True
            return existing_node.kb_id, False

        # 3. 安全等级一致性校验 (§三.2 铁律)
        # 必须安全等级完全一致才可复用已有切片，否则强制重新解析
        reuse_possible = False
        existing_chunks_query = select(KnowledgeChunk).where(
            KnowledgeChunk.physical_file_id == physical_file.file_id,
            KnowledgeChunk.is_deleted == False,
            KnowledgeChunk.security_level == security_level
        ).limit(1)

        existing_chunk = (await db.execute(existing_chunks_query)).scalars().first()
        if existing_chunk:
            reuse_possible = True

        # 4. 创建逻辑节点
        new_node = KnowledgeBaseHierarchy(
            kb_name=filename,
            kb_type=KBTypeEnum.FILE,
            kb_tier=kb_tier,
            parent_id=parent_id,
            security_level=security_level,
            owner_id=user_id,
            dept_id=dept_id,
            physical_file_id=physical_file.file_id,
            parse_status="READY" if reuse_possible else "UPLOADED"
        )
        db.add(new_node)
        await db.flush()

        return new_node.kb_id, not reuse_possible

    @staticmethod
    async def delete_node(db: AsyncSession, kb_id: int, user_id: int):
        """
        WITH RECURSIVE 级联软删除 (§三.2)
        """
        # 1. 递归查询子树
        query = text("""
            WITH RECURSIVE sub_tree AS (
                SELECT kb_id FROM knowledge_base_hierarchy WHERE kb_id = :kb_id
                UNION ALL
                SELECT h.kb_id FROM knowledge_base_hierarchy h
                INNER JOIN sub_tree st ON h.parent_id = st.kb_id
            )
            SELECT kb_id FROM sub_tree;
        """)
        result = await db.execute(query, {"kb_id": kb_id})
        target_ids = [row[0] for row in result.all()]
        
        if not target_ids:
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # 2. 批量更新逻辑树
        await db.execute(
            update(KnowledgeBaseHierarchy)
            .where(KnowledgeBaseHierarchy.kb_id.in_(target_ids))
            .values(is_deleted=True, deleted_at=now)
        )
        
        # 3. 批量失效向量切片 (§三.2 铁律)
        await db.execute(
            update(KnowledgeChunk)
            .where(KnowledgeChunk.kb_id.in_(target_ids))
            .values(is_deleted=True, embedding=None) # 彻底移除向量
        )
        
        # 4. 记录审计
        audit = NBSWorkflowAudit(
            doc_id=None, # 知识库操作无 doc_id
            workflow_node_id=99, # 预留删除节点
            operator_id=user_id,
            action_details={"target_kb_ids": target_ids, "action": "CASCADE_SOFT_DELETE"}
        )
        db.add(audit)
        await db.commit()