from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.system import AsyncTask
from app.models.enums import TaskStatus
from app.schemas.sse import TicketRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.sse_utils import generate_sse_ticket, consume_sse_ticket, verify_task_owner
import asyncio
import json
from app.core.locks import redis_client

router = APIRouter()

@router.post("/ticket")
async def get_ticket(req: TicketRequest, current_user: SystemUser = Depends(get_current_user)):
    # 特殊处理全局通知票据
    if req.task_id == "user_events":
        ticket = await generate_sse_ticket("user_events", current_user.user_id)
        return {"code": 200, "message": "success", "data": {"ticket": ticket}}

    is_owner = await verify_task_owner(req.task_id, current_user.user_id)
    if not is_owner:
        raise BusinessException(403, "无权访问此任务的通知")
    
    ticket = await generate_sse_ticket(req.task_id, current_user.user_id)
    return {"code": 200, "message": "success", "data": {"ticket": ticket}}

@router.get("/{task_id}/events")
async def task_events(request: Request, task_id: str, ticket: str = Query(...), db: AsyncSession = Depends(get_db)):
    ticket_data = await consume_sse_ticket(ticket)
    if not ticket_data or ticket_data.get("task_id") != task_id:
        raise BusinessException(403, "无效或已过期的票据")
        
    async def event_generator():
        # 1. 先检查数据库状态，防止错过已完成的任务 (Race Condition Fix)
        result = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
        task = result.scalars().first()
        if task:
            if task.task_status == TaskStatus.COMPLETED:
                yield f"event: task.completed\ndata: {json.dumps({'event': 'task.completed', 'task_id': task_id, 'result_summary': task.result_summary})}\n\n"
                return
            elif task.task_status == TaskStatus.FAILED:
                yield f"event: task.failed\ndata: {json.dumps({'event': 'task.failed', 'task_id': task_id, 'error_message': task.error_message})}\n\n"
                return

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task_events:{task_id}")
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    data_obj = json.loads(message['data'])
                    event_type = data_obj.get("event", "task.progress")
                    yield f"event: {event_type}\ndata: {message['data']}\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"task_events:{task_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/user-events")
async def user_events(request: Request, ticket: str = Query(...)):
    ticket_data = await consume_sse_ticket(ticket)
    if not ticket_data or ticket_data.get("task_id") != "user_events":
        raise BusinessException(403, "无效或已过期的票据")
    
    user_id = ticket_data.get("user_id")
        
    async def event_generator():
        pubsub = redis_client.pubsub()
        # 订阅个人频道
        await pubsub.subscribe(f"user_events:{user_id}")
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"user_events:{user_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")