from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.models.knowledge import KnowledgeChunk, KnowledgeBaseHierarchy
from app.models.enums import DataSecurityLevel
from app.core.ollama_client import stream_generate, get_embedding
from typing import List, Dict, AsyncGenerator
import json
import os

RRF_K = 60


class RRAGService:
    @staticmethod
    async def _expand_to_leaves(db: AsyncSession, kb_ids: List[int]) -> List[int]:
        """Recursively expand directory nodes to all descendant leaf FILE IDs."""
        cte = text("""
            WITH RECURSIVE sub_tree AS (
                SELECT kb_id, parent_id, kb_type FROM knowledge_base_hierarchy
                WHERE kb_id = ANY(:ids) AND is_deleted = FALSE
                UNION ALL
                SELECT k.kb_id, k.parent_id, k.kb_type
                FROM knowledge_base_hierarchy k
                INNER JOIN sub_tree s ON k.parent_id = s.kb_id
                WHERE k.is_deleted = FALSE
            )
            SELECT kb_id FROM sub_tree WHERE kb_type = 'FILE'
        """)
        result = await db.execute(cte, {"ids": kb_ids})
        return [row[0] for row in result.all()]

    @staticmethod
    async def _vector_search(db: AsyncSession, embedding: List[float], leaf_ids: List[int], top_k: int) -> List[Dict]:
        """HNSW cosine similarity search using pgvector <=> operator."""
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        q = text("""
            SELECT c.chunk_id, c.content, c.metadata_json, c.security_level,
                   1 - (c.embedding <=> :vec) AS score
            FROM knowledge_chunks c
            WHERE c.kb_id = ANY(:leaf_ids)
              AND c.is_deleted = FALSE
              AND c.security_level != 'CORE'
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> :vec
            LIMIT :top_k
        """)
        result = await db.execute(q, {
            "vec": vec_str,
            "leaf_ids": leaf_ids,
            "top_k": top_k
        })
        return [dict(row._mapping) for row in result.all()]

    @staticmethod
    async def _text_search(db: AsyncSession, query: str, leaf_ids: List[int], top_k: int) -> List[Dict]:
        """Full-text search using PostgreSQL ts_rank (BM25-like)."""
        q = text("""
            SELECT c.chunk_id, c.content, c.metadata_json, c.security_level,
                   ts_rank(to_tsvector('simple', c.content), plainto_tsquery('simple', :query)) AS score
            FROM knowledge_chunks c
            WHERE c.kb_id = ANY(:leaf_ids)
              AND c.is_deleted = FALSE
              AND c.security_level != 'CORE'
              AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', :query)
            ORDER BY score DESC
            LIMIT :top_k
        """)
        result = await db.execute(q, {
            "query": query,
            "leaf_ids": leaf_ids,
            "top_k": top_k
        })
        return [dict(row._mapping) for row in result.all()]

    @staticmethod
    def _rrf_fusion(vector_results: List[Dict], text_results: List[Dict], top_k: int) -> List[Dict]:
        """Reciprocal Rank Fusion combining vector and text result lists."""
        scores: Dict[int, float] = {}
        chunk_map: Dict[int, Dict] = {}

        for rank, chunk in enumerate(vector_results, start=1):
            cid = chunk["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank)
            chunk_map[cid] = chunk

        for rank, chunk in enumerate(text_results, start=1):
            cid = chunk["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank)
            chunk_map[cid] = chunk

        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        return [{
            "chunk_id": chunk_map[cid]["chunk_id"],
            "content": chunk_map[cid]["content"],
            "metadata": chunk_map[cid].get("metadata_json", {}),
            "security_level": chunk_map[cid]["security_level"],
        } for cid in sorted_ids]

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
        HRAG hybrid search: HNSW (vector) + BM25 (full-text) + RRF fusion
        """
        if not context_kb_ids:
            return []

        # 1. Recursively expand directory nodes to leaf FILE IDs
        leaf_ids = await RRAGService._expand_to_leaves(db, context_kb_ids)
        if not leaf_ids:
            return []

        # 2. Get query embedding (fallback to text-only on failure)
        vector_results = []
        try:
            embedding = await get_embedding(query_text)
            vector_results = await RRAGService._vector_search(db, embedding, leaf_ids, top_k * 2)
        except Exception:
            pass  # Embedding failed, use text search only

        # 3. Full-text search
        text_results = await RRAGService._text_search(db, query_text, leaf_ids, top_k * 2)

        # 4. RRF fusion
        if vector_results or text_results:
            return RRAGService._rrf_fusion(vector_results, text_results, top_k)
        return []

    @staticmethod
    async def stream_chat_response(
        db: AsyncSession,
        query: str,
        user_id: int,
        dept_id: int | None,
        context_kb_ids: List[int] = []
    ) -> AsyncGenerator[str, None]:
        """Core logic: retrieval, prompt assembly, and streaming generation"""
        # 1. Hybrid retrieval
        context_chunks = await RRAGService.hybrid_search(
            db, query, user_id, dept_id, context_kb_ids
        )

        # 2. Anti-hallucination guard: empty context -> direct fallback
        if not context_chunks:
            yield f"data: {json.dumps({'text': '未探明对应统计线索'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'citations': []}, ensure_ascii=False)}\n\n"
            return

        # 3. Load system prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "system_chat.txt")
        template = "Please answer based on context.\nContext: {context}\nQuestion: {query}"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()

        full_prompt = RRAGService.construct_prompt(template, context_chunks, query)

        # 4. Stream from Ollama
        try:
            async for token in stream_generate(full_prompt):
                yield f"data: {json.dumps({'text': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'AI engine error: {str(e)}'}, ensure_ascii=False)}\n\n"
            return

        citations = [c['metadata'].get('title_path', 'unknown') for c in context_chunks]
        yield f"data: {json.dumps({'done': True, 'citations': citations}, ensure_ascii=False)}\n\n"

    @staticmethod
    def construct_prompt(template: str, context_chunks: List[Dict], query: str) -> str:
        if not context_chunks:
            return template.format(context="No relevant records found", query=query)

        context_str = "\n\n".join([
            f"--- Source: {c['metadata'].get('title_path', 'unknown')} ---\n{c['content']}"
            for c in context_chunks
        ])
        return template.format(context=context_str, query=query)
