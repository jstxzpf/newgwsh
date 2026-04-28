from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
import asyncio
import httpx
import json
from app.core.config import settings

class ChatService:
    @staticmethod
    async def get_embedding(text_input: str) -> Optional[List[float]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text_input},
                    timeout=30
                )
                resp.raise_for_status()
                return resp.json()["embedding"]
        except Exception as e:
            print(f"[Ollama] Embedding failed: {e}")
            return None

    @staticmethod
    async def hybrid_search(db: AsyncSession, query: str, context_kb_ids: List[int], user_id: int, dept_id: int = None, role_level: int = 1):
        if not context_kb_ids: return []
        embedding = await ChatService.get_embedding(query)
        
        vector_clause = ""
        vector_params = {}
        if embedding:
            embedding_str = f"[{','.join(map(str, embedding))}]"
            vector_clause = "(1 - (c.embedding <=> :query_embedding::vector)) as vector_score,"
            vector_params["query_embedding"] = embedding_str
        else:
            vector_clause = "0.0 as vector_score,"

        fts_config = getattr(settings, "FULLTEXT_SEARCH_CONFIG", "simple")
        sql = f"""
        WITH RECURSIVE kb_tree AS (
            SELECT kb_id, owner_id, dept_id, kb_tier, is_deleted 
            FROM knowledge_base_hierarchy 
            WHERE kb_id = ANY(:kb_ids) AND is_deleted = FALSE
            UNION ALL
            SELECT h.kb_id, h.owner_id, h.dept_id, h.kb_tier, h.is_deleted 
            FROM knowledge_base_hierarchy h
            INNER JOIN kb_tree t ON h.parent_id = t.kb_id
            WHERE h.is_deleted = FALSE
        ),
        valid_kbs AS (
            SELECT kb_id FROM kb_tree
            WHERE (kb_tier = 'BASE') OR (kb_tier = 'DEPT' AND dept_id = :dept_id) OR (kb_tier = 'PERSONAL' AND owner_id = :user_id)
        ),
        vector_search AS (
            SELECT c.chunk_id, c.content, c.metadata_json, c.security_level,
                   ROW_NUMBER() OVER (ORDER BY c.embedding <=> :query_embedding::vector) as rank,
                   {vector_clause.replace(',', '') if embedding else '0.0 as vector_score'}
            FROM knowledge_chunks c
            WHERE c.kb_id IN (SELECT kb_id FROM valid_kbs) AND c.is_deleted = FALSE
            LIMIT :vector_top_k
        ),
        text_search AS (
            SELECT c.chunk_id, c.content, c.metadata_json, c.security_level,
                   ROW_NUMBER() OVER (ORDER BY ts_rank_cd(to_tsvector('{fts_config}', c.content), plainto_tsquery('{fts_config}', :query)) DESC) as rank
            FROM knowledge_chunks c
            WHERE c.kb_id IN (SELECT kb_id FROM valid_kbs) AND c.is_deleted = FALSE
              AND to_tsvector('{fts_config}', c.content) @@ plainto_tsquery('{fts_config}', :query)
            LIMIT :bm25_top_k
        )
        SELECT COALESCE(v.chunk_id, t.chunk_id) as chunk_id, COALESCE(v.content, t.content) as content,
               COALESCE(v.metadata_json, t.metadata_json) as metadata_json,
               COALESCE(v.vector_score, 0.0) as vector_score,
               COALESCE(1.0 / (:rrf_k + v.rank), 0.0) + COALESCE(1.0 / (:rrf_k + t.rank), 0.0) as rrf_score
        FROM vector_search v FULL OUTER JOIN text_search t ON v.chunk_id = t.chunk_id
        ORDER BY rrf_score DESC LIMIT :top_k_final;
        """
        params = {"kb_ids": context_kb_ids, "user_id": user_id, "dept_id": dept_id, "query": query,
                  "vector_top_k": settings.RAG_VECTOR_TOP_K, "bm25_top_k": settings.RAG_BM25_TOP_K,
                  "rrf_k": settings.RAG_RRF_K, "top_k_final": settings.RAG_TOP_K_FINAL,
                  "query_embedding": f"[{','.join(['0.0']*1024)}]" }
        params.update(vector_params)
        result = await db.execute(text(sql), params)
        return result.mappings().all()

    @staticmethod
    async def generate_chat_response(db: AsyncSession, query: str, context_kb_ids: List[int], user_id: int, dept_id: int = None, role_level: int = 1):
        if not context_kb_ids: return "未挂载任何统计台账，请先选择上下文。"
        chunks = await ChatService.hybrid_search(db, query, context_kb_ids, user_id, dept_id, role_level)
        if not chunks: return "未检索到相关统计线索。"

        context_text = "\n\n".join([f"资料 #{i+1}: {c['content']}" for i, c in enumerate(chunks)])
        prompt = f"你是一个专业的统计政务助手。请基于以下参考资料回答用户问题。若资料不足，请告知用户。\n\n参考资料：\n{context_text}\n\n问题：{query}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=120
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
