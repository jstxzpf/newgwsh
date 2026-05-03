from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatStreamRequest
from app.models.user import SystemUser
from app.api.dependencies import get_current_user
import asyncio

router = APIRouter()

@router.post("/stream")
async def chat_stream(req: ChatStreamRequest, current_user: SystemUser = Depends(get_current_user)):
    # 模拟 HNSW + BM25 的 RAG 召回与流式回答
    async def fake_ollama_stream():
        yield "data: {\"content\": \"根据挂载的统计台账，\"}\n\n"
        await asyncio.sleep(0.5)
        yield "data: {\"content\": \"2024年一季度总产值为...\"}\n\n"
        await asyncio.sleep(0.5)
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(fake_ollama_stream(), media_type="text/event-stream")