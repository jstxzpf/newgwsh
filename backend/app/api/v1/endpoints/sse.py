import asyncio
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.core.redis import redis_client
import uuid

router = APIRouter()

@router.post("/ticket")
async def create_sse_ticket(task_id: str, user_id: int):
    # TODO: Verify task_owner:{task_id} == user_id in production
    ticket = str(uuid.uuid4())
    # 票据 TTL 15 秒，阅后即焚
    await redis_client.set(f"sse_ticket:{ticket}", task_id, ex=15)
    return {"ticket": ticket}

@router.get("/{task_id}/events")
async def sse_events(task_id: str, ticket: str, request: Request):
    # 1. 校验票据
    stored_task_id = await redis_client.get(f"sse_ticket:{ticket}")
    if not stored_task_id or stored_task_id != task_id:
        raise HTTPException(status_code=403, detail="Invalid or expired ticket")
    
    # 2. 阅后即焚 (连接建立后立即失效)
    await redis_client.delete(f"sse_ticket:{ticket}")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            data = await redis_client.get(f"task_status:{task_id}")
            if data:
                yield f"data: {data}\n\n"
                status_obj = json.loads(data)
                if status_obj["status"] in ["COMPLETED", "FAILED"]:
                    break
            
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
