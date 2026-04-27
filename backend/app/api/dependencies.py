from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from app.core.redis import redis_client
from app.core.config import settings
from app.core.database import get_async_db
from app.models.user import User
from app.core.security import ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
    result = await db.execute(select(User).where(User.user_id == user_id, User.is_active == True))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    # 【对齐修复】向日志上下文注入身份
    import structlog
    structlog.contextvars.bind_contextvars(user_id=user.user_id)
    
    return user

class RateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
        
    async def __call__(self, current_user: User = Depends(get_current_user)):
        user_id = current_user.user_id
        # 简易基于 Redis 的固定窗口限流
        key = f"rate_limit:{user_id}:ai_compute"
        
        current = await redis_client.get(key)
        if current and int(current) >= self.requests:
            raise HTTPException(status_code=429, detail="算力请求过于频繁，请稍后再试。")
            
        pipeline = redis_client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, self.window, nx=True)
        await pipeline.execute()
        return user_id

ai_rate_limiter = RateLimiter(
    requests=settings.AI_RATE_LIMIT_REQUESTS, 
    window=settings.AI_RATE_LIMIT_WINDOW_SECONDS
)
