from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.chat_service import ChatService
from pydantic import BaseModel
from typing import List
from app.api.dependencies import ai_rate_limiter

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    context_kb_ids: List[int] = []

@router.post("/", dependencies=[Depends(ai_rate_limiter)])
async def chat_with_hrag(
    payload: ChatRequest,
    user_id: int = 1, # 临时 Mock
    dept_id: int = 1, # 临时 Mock
    db: AsyncSession = Depends(get_async_db)
):
    try:
        answer = await ChatService.generate_chat_response(
            db, 
            query=payload.query, 
            context_kb_ids=payload.context_kb_ids, 
            user_id=user_id, 
            dept_id=dept_id
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
