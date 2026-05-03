from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import SystemUser
from app.core.exceptions import BusinessException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> SystemUser:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise BusinessException(401, "无效的认证凭证")
    except JWTError:
        raise BusinessException(401, "凭证已过期或无效")
        
    result = await db.execute(select(SystemUser).where(SystemUser.user_id == int(user_id)))
    user = result.scalars().first()
    if not user:
        raise BusinessException(401, "用户不存在")
    if not user.is_active:
        raise BusinessException(403, "账号已被停用")
    return user