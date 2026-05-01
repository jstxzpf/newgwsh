import json
import redis.asyncio as redis
from app.core.config import settings

async def publish_user_event(user_id: int, event_type: str, data: dict):
    """
    向 Redis Pub/Sub 发送个人全局事件 (用于 SSE 推送)
    """
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    payload = {
        "event": event_type,
        "data": data
    }
    await r.publish(f"user_channel:{user_id}", json.dumps(payload))
    await r.close()
