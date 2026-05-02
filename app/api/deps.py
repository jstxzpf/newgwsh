from typing import AsyncGenerator, Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.org import SystemUser
from app.core import security
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_async_db),
    token: str = Depends(oauth2_scheme)
) -> SystemUser:
    """获取当前用户并验证 is_active 状态及单设备登录 (核心防线)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        access_jti: str = payload.get("jti")
        if user_id is None or token_type != "access" or access_jti is None:
            raise credentials_exception
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception
    
    # 1. 单设备登录校验 (实施约束规则 7)
    from app.models.org import UserSession
    stmt_session = select(UserSession).where(UserSession.user_id == int(user_id)).order_by(UserSession.created_at.desc())
    session_res = await db.execute(stmt_session)
    session = session_res.scalars().first()
    
    # 如果会话不存在或 access_jti 不匹配（说明已被踢出或登出）
    if not session or session.access_jti != access_jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SESSION_KICKED", # 对应前端 401 细分处理铁律
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 数据库核身
    from sqlalchemy.orm import selectinload
    stmt = select(SystemUser).where(SystemUser.user_id == int(user_id)).options(selectinload(SystemUser.department))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # 3. 全局强制 is_active 检查 (P0 级铁律)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user

async def get_current_active_user(
    current_user: SystemUser = Depends(get_current_user)
) -> SystemUser:
    """确认用户活跃 (冗余检查，get_current_user 已包含)"""
    return current_user

async def get_current_admin_user(
    current_user: SystemUser = Depends(get_current_user)
) -> SystemUser:
    """管理员权限检查"""
    if current_user.role_level < 99:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
