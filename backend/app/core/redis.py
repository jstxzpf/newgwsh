import redis.asyncio as redis
from app.core.config import settings

_redis_client = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client
