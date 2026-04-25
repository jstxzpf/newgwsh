from fastapi import HTTPException, Depends
from app.core.redis import redis_client

class RateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
        
    async def __call__(self, user_id: int = 1): # 临时 mock user_id
        # 简易基于 Redis 的固定窗口限流
        key = f"rate_limit:{user_id}:ai_compute"
        
        current = await redis_client.get(key)
        if current and int(current) >= self.requests:
            raise HTTPException(status_code=429, detail="算力请求过于频繁，请稍后再试。")
            
        pipeline = redis_client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, self.window, nx=True) # 仅在 key 刚创建时设置过期
        await pipeline.execute()
        return user_id

ai_rate_limiter = RateLimiter(requests=5, window=60)
