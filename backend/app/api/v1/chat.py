from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import SystemUser
from app.schemas.chat import ChatRequest
from app.api.dependencies import get_current_user
from app.services.rrag_service import RRAGService
from app.core.exceptions import BusinessException
import asyncio
import os

router = APIRouter()

@router.post("/stream")
async def chat_stream(req: ChatRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    流式问答路由：整合 HRAG 检索与 LLM 输出
    """
    # 1. 混合检索召回 (HNSW + BM25)
    context_chunks = await RRAGService.hybrid_search(
        db, req.query, current_user.user_id, current_user.dept_id, req.context_kb_ids
    )

    # 2. 加载 System Prompt (铁律 §八.8)
    prompt_path = os.path.join(os.path.dirname(__file__), "../../../prompts/system_chat.txt")
    if not os.path.exists(prompt_path):
        # Fallback
        template = "请依据上下文回答问题。\n上下文：{context}\n问题：{query}"
    else:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

    full_prompt = RRAGService.construct_prompt(template, context_chunks, req.query)

    # 3. 模拟流式输出生成器
    async def event_generator():
        # 实际应调用 Ollama / LLM SDK
        # 这里模拟打字机效果
        message = f"根据泰兴调查队的统计资料，关于您提到的‘{req.query}’，相关情况如下：\n\n"
        if not context_chunks:
            message = "未探明对应统计线索。"
        else:
            message += f"检索到 {len(context_chunks)} 条相关台账记录..."
        
        for word in message:
            yield f"data: {json.dumps({'text': word})}\n\n"
            await asyncio.sleep(0.02)
        
        # 结尾推送引用来源 (ToolTips §三.6)
        citations = [c['metadata'].get('title_path', '未知') for c in context_chunks]
        yield f"data: {json.dumps({'done': True, 'citations': citations})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

import json