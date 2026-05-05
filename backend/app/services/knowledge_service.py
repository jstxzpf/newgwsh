from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk, KnowledgePhysicalFile
from app.models.system import NBSWorkflowAudit
from app.models.enums import WorkflowNodeId, KBTypeEnum, KBTier, DataSecurityLevel
from datetime import datetime, timezone
import hashlib

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
    ) -> int:
        # 1. 物理去重预检 (Task 4 §三.5)
        content_hash = hashlib.sha256(content).hexdigest()
        
        result = await db.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == content_hash))
        physical_file = result.scalars().first()
        
        if not physical_file:
            # 模拟存储物理文件
            file_path = f"/app/data/uploads/{content_hash}_{filename}"
            physical_file = KnowledgePhysicalFile(
                content_hash=content_hash,
                file_path=file_path,
                file_size=len(content)
            )
            db.add(physical_file)
            await db.flush()
        
        # 2. 安全等级一致性校验 (§三.2 铁律)
        # 检查是否有现成的 Ready 切片且安全等级一致
        reuse_possible = False
        existing_chunks_query = select(KnowledgeChunk).where(
            KnowledgeChunk.physical_file_id == physical_file.file_id,
            KnowledgeChunk.is_deleted == False,
            KnowledgeChunk.security_level == security_level # 必须完全一致才可复用
        ).limit(1)
        
        existing_chunk = (await db.execute(existing_chunks_query)).scalars().first()
        if existing_chunk:
            reuse_possible = True

        # 3. 创建逻辑节点
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
        
        if reuse_possible:
            # 执行切片复用关联 (逻辑层完成，不复制物理数据)
            pass 

        return new_node.kb_id

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
            doc_id="N/A", # 知识库操作无 doc_id
            workflow_node_id=99, # 预留删除节点
            operator_id=user_id,
            action_details={"target_kb_ids": target_ids, "action": "CASCADE_SOFT_DELETE"}
        )
        db.add(audit)
        await db.commit()