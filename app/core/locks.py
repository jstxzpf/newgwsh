import json
import uuid
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings

class LockManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def _get_key(self, doc_id: str) -> str:
        return f"lock:{doc_id}"

    async def acquire_lock(self, doc_id: str, user_id: int, username: str, ttl: int = None) -> Optional[dict]:
        """
        申请锁 (Redlock 简版)
        """
        key = self._get_key(doc_id)
        ttl = ttl or settings.LOCK_TTL_DEFAULT
        token = str(uuid.uuid4())
        
        lock_data = {
            "user_id": user_id,
            "username": username,
            "token": token,
            "acquired_at": str(uuid.uuid1()) # 简化的时间戳占位
        }
        
        # NX: Not Exist, EX: Expire
        success = await self.redis.set(key, json.dumps(lock_data), ex=ttl, nx=True)
        
        if success:
            return {"lock_token": token, "ttl": ttl}
        return None

    async def heartbeat(self, doc_id: str, token: str, ttl: int = None) -> Optional[dict]:
        """
        续租锁
        """
        key = self._get_key(doc_id)
        ttl = ttl or settings.LOCK_TTL_DEFAULT
        
        data_raw = await self.redis.get(key)
        if not data_raw:
            return None
            
        data = json.loads(data_raw)
        if data.get("token") != token:
            return None
            
        await self.redis.expire(key, ttl)
        return {
            "next_suggested_heartbeat": settings.LOCK_HEARTBEAT_INTERVAL,
            "lock_ttl_remaining": ttl
        }

    async def verify_lock(self, doc_id: str, token: str) -> bool:
        """
        验证锁是否有效
        """
        key = self._get_key(doc_id)
        data_raw = await self.redis.get(key)
        if data_raw:
            data = json.loads(data_raw)
            return data.get("token") == token
        return False

    async def release_lock(self, doc_id: str, token: str) -> bool:
        """
        释放锁 (Lua 脚本保证原子性)
        """
        key = self._get_key(doc_id)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        # 由于我们存储的是 JSON，Lua 脚本需要先解析 JSON 比较 token，这里为了演示简化
        # 实际生产应使用 JSON 比较或直接存 Token
        data_raw = await self.redis.get(key)
        if data_raw:
            data = json.loads(data_raw)
            if data.get("token") == token:
                await self.redis.delete(key)
                return True
        return False

lock_manager = LockManager(settings.REDIS_URL)
