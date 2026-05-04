import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

async def acquire_redis_lock(doc_id: str, user_id: int, username: str, token: str, ttl: int = 180) -> bool:
    lock_key = f"lock:{doc_id}"
    value = f'{{"user_id": {user_id}, "username": "{username}", "token": "{token}"}}'
    # NX: 只有不存在时才设置，EX: 过期时间
    return await redis_client.set(lock_key, value, nx=True, ex=ttl)

async def release_redis_lock(doc_id: str, user_id: int, token: str) -> bool:
    lock_key = f"lock:{doc_id}"
    import json
    value = await redis_client.get(lock_key)
    if value:
        try:
            data = json.loads(value)
            if data.get("user_id") == user_id and data.get("token") == token:
                await redis_client.delete(lock_key)
                return True
        except:
            pass
    return False

async def extend_redis_lock(doc_id: str, user_id: int, token: str, ttl: int = 180) -> bool:
    lock_key = f"lock:{doc_id}"
    import json
    value = await redis_client.get(lock_key)
    if value:
        try:
            data = json.loads(value)
            if data.get("user_id") == user_id and data.get("token") == token:
                await redis_client.expire(lock_key, ttl)
                return True
        except:
            pass
    return False

async def list_all_locks() -> list:
    keys = await redis_client.keys("lock:*")
    locks = []
    for k in keys:
        val = await redis_client.get(k)
        if val:
            try:
                import json
                data = json.loads(val)
                data["doc_id"] = k.split(":")[1]
                data["ttl"] = await redis_client.ttl(k)
                locks.append(data)
            except:
                pass
    return locks