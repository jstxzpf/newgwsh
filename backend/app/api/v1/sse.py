from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from app.models.user import SystemUser
from app.schemas.sse import TicketRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.sse_utils import generate_sse_ticket, consume_sse_ticket, verify_task_owner
import asyncio
from app.core.locks import redis_client

router = APIRouter()

@router.post("/ticket")
async def get_ticket(req: TicketRequest, current_user: SystemUser = Depends(get_current_user)):
    is_owner = await verify_task_owner(req.task_id, current_user.user_id)
    if not is_owner:
        raise BusinessException(403, "无权访问此任务的通知")
    
    ticket = await generate_sse_ticket(req.task_id, current_user.user_id)
    return {"code": 200, "message": "success", "data": {"ticket": ticket}}

@router.get("/{task_id}/events")
async def task_events(request: Request, task_id: str, ticket: str = Query(...)):
    # 验证票据（阅后即焚）
    ticket_data = await consume_sse_ticket(ticket)
    if not ticket_data or ticket_data.get("task_id") != task_id:
        raise BusinessException(403, "无效或已过期的票据，请重新申请")
        
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task_events:{task_id}")
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    data = message['data']
                    yield f"event: task_update\ndata: {data}\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"task_events:{task_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")