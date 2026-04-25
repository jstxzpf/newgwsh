import uuid
import json
from datetime import datetime
from app.core.redis import redis_client
from app.core.config import settings

class LockService:
    @staticmethod
    async def acquire_lock(doc_id: str, user_id: int, username: str) -> str | None:
        lock_key = f"lock:{doc_id}"
        token = str(uuid.uuid4())
        lock_data = {
            "user_id": user_id,
            "username": username,
            "acquired_at": datetime.now().isoformat(),
            "token": token
        }
        # 使用 NX (Not Exists) 和 EX (Expire) 保证原子性
        success = await redis_client.set(
            lock_key, 
            json.dumps(lock_data), 
            nx=True, 
            ex=settings.LOCK_TTL_SECONDS
        )
        return token if success else None

    @staticmethod
    async def release_lock(doc_id: str, token: str) -> bool:
        lock_key = f"lock:{doc_id}"
        current_lock = await redis_client.get(lock_key)
        if not current_lock:
            return True
        
        data = json.loads(current_lock)
        if data.get("token") == token:
            await redis_client.delete(lock_key)
            return True
        return False

    @staticmethod
    async def heartbeat(doc_id: str, token: str) -> bool:
        lock_key = f"lock:{doc_id}"
        current_lock = await redis_client.get(lock_key)
        if not current_lock:
            return False
        
        data = json.loads(current_lock)
        if data.get("token") == token:
            await redis_client.expire(lock_key, settings.LOCK_TTL_SECONDS)
            return True
        return False
