from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import SystemUser
from app.schemas.chat import ChatRequest
from app.api.dependencies import get_current_user
from app.services.rrag_service import RRAGService

router = APIRouter()

@router.post("/stream")
async def chat_stream(req: ChatRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    流式问答路由：职责解耦，仅负责解析请求与分发生成器 (§一.11)
    """
    return StreamingResponse(
        RRAGService.stream_chat_response(
            db, req.query, current_user.user_id, current_user.dept_id, req.context_kb_ids
        ), 
        media_type="text/event-stream"
    )