from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from app.models.knowledge import KnowledgeChunk, KnowledgeBaseHierarchy
from app.models.enums import DataSecurityLevel, KBTier
from typing import List, Dict, AsyncGenerator
import json
import os
import asyncio

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
        """
        # 简化版实现
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
        核心逻辑解耦：整合检索、Prompt 装配与流式生成 (§一.11)
        """
        # 1. 混合检索召回
        context_chunks = await RRAGService.hybrid_search(
            db, query, user_id, dept_id, context_kb_ids
        )

        # 2. 加载 System Prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/system_chat.txt")
        template = "请依据上下文回答问题。\n上下文：{context}\n问题：{query}"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()

        full_prompt = RRAGService.construct_prompt(template, context_chunks, query)
        
        # 3. 模拟生成器逻辑 (未来对接 Ollama SDK)
        message = f"根据泰兴调查队的统计资料，关于您提到的‘{query}’，相关情况如下：\n\n"
        if not context_chunks:
            message = "未探明对应统计线索。"
        else:
            message += f"检索到 {len(context_chunks)} 条相关台账记录..."
        
        for word in message:
            yield f"data: {json.dumps({'text': word})}\n\n"
            await asyncio.sleep(0.01)
        
        citations = [c['metadata'].get('title_path', '未知') for c in context_chunks]
        yield f"data: {json.dumps({'done': True, 'citations': citations})}\n\n"

    @staticmethod
    def construct_prompt(template: str, context_chunks: List[Dict], query: str) -> str:
        if not context_chunks:
            return template.format(context="未探明对应统计线索", query=query)
        
        context_str = "\n\n".join([
            f"--- 来源: {c['metadata'].get('title_path', '未知')} ---\n{c['content']}"
            for c in context_chunks
        ])
        return template.format(context=context_str, query=query)