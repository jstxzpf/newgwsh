from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sse_starlette.sse import EventSourceResponse
from app.api import deps
from app.models.org import SystemUser
from app.models.knowledge import KnowledgeChunk, KnowledgeBaseHierarchy, KbTier, SecurityLevel
from app.services.ai_service import ai_service
from app.schemas.response import StandardResponse, success, error
from pydantic import BaseModel
import json
import asyncio

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    context_kb_ids: List[int] = []

@router.post("/stream")
async def stream_chat(
    req: ChatRequest,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """
    流式问答 (HRAG): 向量检索 + BM25 全文检索 + RRF 融合 + SSE 输出 (P9)
    """
    # 1. 混合检索与 RRF 融合 (同之前的逻辑)
    query_vector = ai_service.get_embedding(req.query)
    
    base_stmt = select(KnowledgeChunk).join(KnowledgeBaseHierarchy).where(
        KnowledgeBaseHierarchy.is_deleted == False,
        KnowledgeChunk.is_deleted == False
    )
    
    if req.context_kb_ids:
        base_stmt = base_stmt.where(KnowledgeBaseHierarchy.kb_id.in_(req.context_kb_ids))
        
    if current_user.role_level < 99:
        from sqlalchemy import or_
        filters = []
        filters.append(KnowledgeChunk.kb_tier == KbTier.BASE)
        filters.append((KnowledgeChunk.kb_tier == KbTier.DEPT) & (KnowledgeChunk.dept_id == current_user.dept_id))
        filters.append((KnowledgeChunk.kb_tier == KbTier.PERSONAL) & (KnowledgeChunk.owner_id == current_user.user_id))
        base_stmt = base_stmt.where(or_(*filters))

    # 向量召回
    vector_stmt = base_stmt.order_by(KnowledgeChunk.embedding.cosine_distance(query_vector)).limit(10)
    vector_result = await db.execute(vector_stmt)
    vector_chunks = vector_result.scalars().all()
    
    # BM25 召回
    from sqlalchemy import func
    bm25_stmt = base_stmt.where(
        func.to_tsvector('zh', KnowledgeChunk.content).op('@@')(func.to_tsquery('zh', req.query))
    ).order_by(
        func.ts_rank_cd(func.to_tsvector('zh', KnowledgeChunk.content), func.to_tsquery('zh', req.query)).desc()
    ).limit(10)
    
    try:
        bm25_result = await db.execute(bm25_stmt)
        bm25_chunks = bm25_result.scalars().all()
    except Exception:
        bm25_chunks = []

    # RRF 融合
    k = 60
    chunk_scores = {}
    chunk_map = {}
    
    for rank, chunk in enumerate(vector_chunks):
        chunk_map[chunk.chunk_id] = chunk
        chunk_scores[chunk.chunk_id] = chunk_scores.get(chunk.chunk_id, 0) + 1.0 / (k + rank + 1)
        
    for rank, chunk in enumerate(bm25_chunks):
        chunk_map[chunk.chunk_id] = chunk
        chunk_scores[chunk.chunk_id] = chunk_scores.get(chunk.chunk_id, 0) + 1.0 / (k + rank + 1)
        
    sorted_candidates = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
    final_chunks = []
    core_discarded_count = 0
    
    for cid, score in sorted_candidates:
        chunk = chunk_map[cid]
        if chunk.security_level == SecurityLevel.CORE:
            core_discarded_count += 1
            continue
        final_chunks.append(chunk)
        if len(final_chunks) >= 5:
            break
            
    if core_discarded_count > 0:
        from app.models.audit import WorkflowAudit
        audit = WorkflowAudit(
            doc_id=None,
            workflow_node_id=20,
            operator_id=current_user.user_id,
            action_details={"action": "rag_filter", "core_discarded_count": core_discarded_count}
        )
        db.add(audit)
        await db.commit()

    if not final_chunks:
        async def empty_generator():
            yield {"data": json.dumps({"answer": "未探明对应统计线索", "done": True})}
        return EventSourceResponse(empty_generator())

    context_text = "\n\n".join([f"<{c.metadata_json.get('title_path', '未知')}>: {c.content}" for c in final_chunks])

    async def event_generator():
        # 先发送参考引用
        references = [{"id": c.chunk_id, "path": c.metadata_json.get('title_path')} for c in final_chunks]
        yield {"event": "references", "data": json.dumps(references)}
        
        # 流式获取 LLM 输出
        for chunk in ai_service.stream_chat_completion("system_chat", req.query, context=context_text):
            if "error" in chunk:
                yield {"event": "error", "data": json.dumps(chunk["error"])}
                break
            
            if chunk.get("done"):
                yield {"event": "done", "data": "[DONE]"}
                break
                
            yield {"data": json.dumps({"token": chunk.get("response", "")})}
            await asyncio.sleep(0.01)

    return EventSourceResponse(event_generator())
