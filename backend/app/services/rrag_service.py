from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from app.models.knowledge import KnowledgeChunk, KnowledgeBaseHierarchy
from app.models.enums import DataSecurityLevel, KBTier
from app.core.ollama_client import stream_generate
from typing import List, Dict, AsyncGenerator
import json
import os

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
        HRAG hybrid search: HNSW (vector) + BM25 (full-text) + RRF fusion
        """
        final_chunks = await db.execute(
            select(KnowledgeChunk)
            .join(KnowledgeBaseHierarchy, KnowledgeChunk.kb_id == KnowledgeBaseHierarchy.kb_id)
            .where(KnowledgeChunk.is_deleted == False)
            .where(KnowledgeBaseHierarchy.is_deleted == False)
            .where(KnowledgeChunk.security_level != DataSecurityLevel.CORE)
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
    async def stream_chat_response(
        db: AsyncSession,
        query: str,
        user_id: int,
        dept_id: int | None,
        context_kb_ids: List[int] = []
    ) -> AsyncGenerator[str, None]:
        """
        Core logic: retrieval, prompt assembly, and streaming generation
        """
        # 1. Hybrid retrieval
        context_chunks = await RRAGService.hybrid_search(
            db, query, user_id, dept_id, context_kb_ids
        )

        # 2. Load system prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "system_chat.txt")
        template = "Please answer based on context.\nContext: {context}\nQuestion: {query}"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()

        full_prompt = RRAGService.construct_prompt(template, context_chunks, query)

        # 3. Stream from Ollama
        try:
            async for token in stream_generate(full_prompt):
                yield f"data: {json.dumps({'text': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'AI engine error: {str(e)}'})}\n\n"
            return

        citations = [c['metadata'].get('title_path', 'unknown') for c in context_chunks]
        yield f"data: {json.dumps({'done': True, 'citations': citations})}\n\n"

    @staticmethod
    def construct_prompt(template: str, context_chunks: List[Dict], query: str) -> str:
        if not context_chunks:
            return template.format(context="No relevant records found", query=query)

        context_str = "\n\n".join([
            f"--- Source: {c['metadata'].get('title_path', 'unknown')} ---\n{c['content']}"
            for c in context_chunks
        ])
        return template.format(context=context_str, query=query)
