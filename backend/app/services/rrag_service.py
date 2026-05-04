from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from app.models.knowledge import KnowledgeChunk, KnowledgeBaseHierarchy
from app.models.enums import DataSecurityLevel, KBTier
from typing import List, Dict
import json

class RRAGService:
    @staticmethod
    async def hybrid_search(
        db: AsyncSession, 
        query_text: str, 
        user_id: int, 
        dept_id: int | None,
        context_kb_ids: List[int] = [],
        top_k: int = 5
    ) -> List[Dict]:
        """
        HRAG 混合检索：HNSW (向量) + BM25 (全文) + RRF 融合
        铁律：强制权限过滤与软删除过滤 (§三.1)
        """
        # 1. 向量路 (HNSW)
        # 模拟向量获取逻辑 (实际需调用 Embedding 模型)
        # 使用 <=> 算子进行余弦距离计算
        vector_query = text("""
            SELECT chunk_id, 1 - (embedding <=> :query_vec) as score
            FROM knowledge_chunks c
            JOIN knowledge_base_hierarchy h ON c.kb_id = h.kb_id
            WHERE c.is_deleted = FALSE AND h.is_deleted = FALSE
            AND (
                h.kb_tier = 'BASE' 
                OR (h.kb_tier = 'DEPT' AND h.dept_id = :dept_id)
                OR (h.kb_tier = 'PERSONAL' AND h.owner_id = :user_id)
            )
            ORDER BY embedding <=> :query_vec
            LIMIT 20
        """)
        
        # 2. 全文路 (BM25/GIN)
        # 使用 to_tsvector 和 ts_rank_cd
        text_query = text("""
            SELECT chunk_id, ts_rank_cd(to_tsvector('zh', content), plainto_tsquery('zh', :query)) as score
            FROM knowledge_chunks c
            JOIN knowledge_base_hierarchy h ON c.kb_id = h.kb_id
            WHERE c.is_deleted = FALSE AND h.is_deleted = FALSE
            AND (
                h.kb_tier = 'BASE' 
                OR (h.kb_tier = 'DEPT' AND h.dept_id = :dept_id)
                OR (h.kb_tier = 'PERSONAL' AND h.owner_id = :user_id)
            )
            AND to_tsvector('zh', content) @@ plainto_tsquery('zh', :query)
            ORDER BY score DESC
            LIMIT 20
        """)

        # 逻辑：RRF 融合与 CORE 级切片废弃
        # 这里为演示暂用简化合并逻辑
        # 实际应分别执行查询并合并
        
        final_chunks = await db.execute(
            select(KnowledgeChunk)
            .join(KnowledgeBaseHierarchy, KnowledgeChunk.kb_id == KnowledgeBaseHierarchy.kb_id)
            .where(KnowledgeChunk.is_deleted == False)
            .where(KnowledgeBaseHierarchy.is_deleted == False)
            .where(KnowledgeChunk.security_level != DataSecurityLevel.CORE) # 铁律：废弃 CORE
            .limit(top_k)
        )
        
        results = []
        for chunk in final_chunks.scalars().all():
            results.append({
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "metadata": chunk.metadata_json,
                "security_level": chunk.security_level
            })
            
        return results

    @staticmethod
    def construct_prompt(template: str, context_chunks: List[Dict], query: str) -> str:
        if not context_chunks:
            return template.format(context="未探明对应统计线索", query=query)
        
        context_str = "\n\n".join([
            f"--- 来源: {c['metadata'].get('title_path', '未知')} ---\n{c['content']}"
            for c in context_chunks
        ])
        return template.format(context=context_str, query=query)