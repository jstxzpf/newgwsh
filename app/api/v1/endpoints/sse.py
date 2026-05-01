import asyncio
import json
from typing import Any, AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from app.api import deps
from app.core.locks import lock_manager
from app.models.org import SystemUser
from app.schemas.response import StandardResponse, success, error

router = APIRouter()

@router.post("/ticket", response_model=StandardResponse)
async def get_sse_ticket(
    task_id: Optional[str] = None, # 任务级 SSE 需要 task_id
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """
    申请 SSE 票据 (阅后即焚 P4.1)
    设计要求: 绑定 task_id (可选) 与 user_id, 15秒 TTL
    """
    import uuid
    ticket_uuid = str(uuid.uuid4())
    ticket_key = f"sse_ticket:{ticket_uuid}"
    
    # 验证任务所有权 (如果是任务级 SSE)
    if task_id:
        task_owner = await lock_manager.redis.get(f"task_owner:{task_id}")
        if task_owner and task_owner != str(current_user.user_id):
            return error(code=403, message="Not authorized for this task")

    ticket_data = {
        "user_id": current_user.user_id,
        "task_id": task_id
    }

    
    # 在 Redis 中暂存这个绑定关系
    await lock_manager.redis.set(ticket_key, json.dumps(ticket_data), ex=15)
    return success(data={"ticket": ticket_uuid})

@router.get("/{task_id}/events")
async def sse_events(
    task_id: str,
    ticket: str,
    request: Request
) -> EventSourceResponse:
    """
    任务进度监听隧道
    """
    # 1. 校验票据并立刻销毁 (阅后即焚铁律 P4.1)
    ticket_key = f"sse_ticket:{ticket}"
    ticket_data_raw = await lock_manager.redis.get(ticket_key)
    if not ticket_data_raw:
        raise HTTPException(status_code=403, detail="Invalid or expired ticket")
    
    await lock_manager.redis.delete(ticket_key)
    ticket_data = json.loads(ticket_data_raw)
    
    if ticket_data.get("task_id") != task_id:
        raise HTTPException(status_code=403, detail="Ticket task mismatch")

    async def event_generator() -> AsyncGenerator[dict, None]:
        # 订阅 Redis Pub/Sub 任务通道
        pubsub = lock_manager.redis.pubsub()
        await pubsub.subscribe(f"task_channel:{task_id}")
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                message = await pubsub.get_message(ignore_subscribe_crashes=True, timeout=1.0)
                if message and message['type'] == 'message':
                    yield {
                        "data": message['data']
                    }
                else:
                    # 心跳
                    yield {"event": "ping", "data": ""}
                
                await asyncio.sleep(1)
        finally:
            await pubsub.unsubscribe(f"task_channel:{task_id}")

    return EventSourceResponse(event_generator())

@router.get("/user-events")
async def user_global_events(
    ticket: str,
    request: Request
) -> EventSourceResponse:
    """
    个人全局监听隧道 (用于 LOCK_RECLAIMED, notification.* 等消息)
    """
    # 1. 校验票据
    ticket_key = f"sse_ticket:{ticket}"
    ticket_data_raw = await lock_manager.redis.get(ticket_key)
    if not ticket_data_raw:
        raise HTTPException(status_code=403, detail="Invalid or expired ticket")
    
    await lock_manager.redis.delete(ticket_key)
    ticket_data = json.loads(ticket_data_raw)
    user_id = ticket_data.get("user_id")

    async def event_generator() -> AsyncGenerator[dict, None]:
        # 订阅 Redis Pub/Sub 个人通道
        pubsub = lock_manager.redis.pubsub()
        channel_name = f"user_channel:{user_id}"
        await pubsub.subscribe(channel_name)
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                message = await pubsub.get_message(ignore_subscribe_crashes=True, timeout=1.0)
                if message and message['type'] == 'message':
                    # 数据格式通常为 {"event": "xxx", "data": {...}}
                    data = json.loads(message['data'])
                    yield {
                        "event": data.get("event", "message"),
                        "data": json.dumps(data.get("data", {}))
                    }
                else:
                    yield {"event": "ping", "data": ""}
                
                await asyncio.sleep(1)
        finally:
            await pubsub.unsubscribe(channel_name)

    return EventSourceResponse(event_generator())
