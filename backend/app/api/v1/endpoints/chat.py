from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.chat_service import ChatService
from pydantic import BaseModel
from typing import List
from app.api.dependencies import ai_rate_limiter
from app.api.dependencies import get_current_user
from app.models.user import User
from fastapi.responses import StreamingResponse
import json
import httpx
from app.core.config import settings

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    context_kb_ids: List[int] = []

@router.post("/", dependencies=[Depends(ai_rate_limiter)])
async def chat_with_hrag(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        answer = await ChatService.generate_chat_response(
            db, query=payload.query, context_kb_ids=payload.context_kb_ids, 
            user_id=current_user.user_id, dept_id=current_user.dept_id, role_level=current_user.role_level
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream", dependencies=[Depends(ai_rate_limiter)])
async def stream_chat_with_hrag(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    async def response_generator():
        try:
            # 1. 混合检索
            chunks = await ChatService.hybrid_search(
                db, payload.query, payload.context_kb_ids, 
                current_user.user_id, current_user.dept_id, current_user.role_level
            )
            if not chunks:
                yield f"data: {json.dumps({'content': '未检索到相关统计线索。', 'is_end': True})}\n\n"
                return

            context_text = "\n\n".join([f"资料 #{i+1}: {c['content']}" for i, c in enumerate(chunks)])
            prompt = f"你是一个专业的统计政务助手。请基于以下参考资料回答用户问题。\n\n参考资料：\n{context_text}\n\n问题：{payload.query}"

            # 2. 调用 Ollama 流式接口
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": True},
                    timeout=120
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line: continue
                        body = json.loads(line)
                        token = body.get("response", "")
                        done = body.get("done", False)
                        yield f"data: {json.dumps({'content': token, 'is_end': done})}\n\n"
                        if done: break
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(response_generator(), media_type="text/event-stream")
