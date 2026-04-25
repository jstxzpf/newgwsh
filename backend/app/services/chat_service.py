from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import asyncio

class ChatService:
    @staticmethod
    async def hybrid_search(
        db: AsyncSession, 
        query: str, 
        context_kb_ids: List[int],
        user_id: int,
        dept_id: int = None
    ):
        if not context_kb_ids:
            return []

        # HRAG 混合检索算法 (pgvector + BM25 + RRF)
        # 这里使用了 text() 配合原始 SQL 以利用 pgvector 算子和全文检索函数
        sql = """
        WITH RECURSIVE kb_tree AS (
            SELECT kb_id, owner_id, kb_tier, is_deleted 
            FROM knowledge_base_hierarchy 
            WHERE kb_id = ANY(:kb_ids) AND is_deleted = FALSE
            
            UNION ALL
            
            SELECT h.kb_id, h.owner_id, h.kb_tier, h.is_deleted 
            FROM knowledge_base_hierarchy h
            INNER JOIN kb_tree t ON h.parent_id = t.kb_id
            WHERE h.is_deleted = FALSE
        ),
        valid_kbs AS (
            SELECT kb_id FROM kb_tree
            WHERE 
                (kb_tier = 'BASE') OR
                (kb_tier = 'DEPT' AND :dept_id IS NOT NULL) OR
                (kb_tier = 'PERSONAL' AND owner_id = :user_id)
        ),
        vector_search AS (
            SELECT c.chunk_id, c.content, c.metadata_json, c.security_level,
                   ROW_NUMBER() OVER (ORDER BY c.embedding <=> :fake_embedding::vector) as rank
            FROM knowledge_chunks c
            JOIN knowledge_base_hierarchy h ON c.kb_id = h.kb_id
            WHERE c.kb_id IN (SELECT kb_id FROM valid_kbs) 
              AND c.is_deleted = FALSE 
              AND h.is_deleted = FALSE
            LIMIT 20
        ),
        text_search AS (
            SELECT c.chunk_id, c.content, c.metadata_json, c.security_level,
                   ROW_NUMBER() OVER (ORDER BY ts_rank_cd(to_tsvector('simple', c.content), plainto_tsquery('simple', :query)) DESC) as rank
            FROM knowledge_chunks c
            JOIN knowledge_base_hierarchy h ON c.kb_id = h.kb_id
            WHERE c.kb_id IN (SELECT kb_id FROM valid_kbs) 
              AND c.is_deleted = FALSE 
              AND h.is_deleted = FALSE
              AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', :query)
            LIMIT 20
        )
        
        -- RRF 融合 (Reciprocal Rank Fusion, k=60)
        SELECT 
            COALESCE(v.chunk_id, t.chunk_id) as chunk_id,
            COALESCE(v.content, t.content) as content,
            COALESCE(v.metadata_json, t.metadata_json) as metadata_json,
            COALESCE(v.security_level, t.security_level) as security_level,
            COALESCE(1.0 / (60 + v.rank), 0.0) + COALESCE(1.0 / (60 + t.rank), 0.0) as rrf_score
        FROM vector_search v
        FULL OUTER JOIN text_search t ON v.chunk_id = t.chunk_id
        WHERE COALESCE(v.security_level, t.security_level) != 'CORE' -- 防御：过滤高绝密切片
        ORDER BY rrf_score DESC
        LIMIT 5;
        """
        
        # 伪造 768 维 0 向量以绕过当前环境限制
        fake_embedding = "[" + ",".join(["0.0"] * 768) + "]"
        
        result = await db.execute(
            text(sql), 
            {
                "kb_ids": context_kb_ids, 
                "user_id": user_id, 
                "dept_id": dept_id, 
                "query": query,
                "fake_embedding": fake_embedding
            }
        )
        
        return result.mappings().all()

    @staticmethod
    async def generate_chat_response(db: AsyncSession, query: str, context_kb_ids: List[int], user_id: int, dept_id: int = None):
        chunks = await ChatService.hybrid_search(db, query, context_kb_ids, user_id, dept_id)
        
        if not chunks:
            # 防幻觉话术
            return "未探明对应统计线索，请尝试调整挂载台账范围或简化提问。"
            
        # 组装上下文
        context_str = "\n\n".join([f"【数据块 #{i+1}】\n{c['content']}" for i, c in enumerate(chunks)])
        
        # 系统提示词注入 (System Prompt Injection)
        # “你是一个严肃政务问答助手。请严格且只能依据下方【挂载上下文】的数据进行总结回答...”
        
        # 模拟调用 Ollama (异步延迟)
        await asyncio.sleep(1.2)
        
        # 返回模拟生成的基于政务语言的回答
        answer = f"[智能问答中枢] 经对您挂载的 {len(chunks)} 份台账进行穿透检索，结果如下：\n\n（这是基于您的提问 '{query}' 和后台检索到的统计数据的自动总结响应，实际环境下将由此处的 Ollama LLM 驱动生成。）"
        return answer
