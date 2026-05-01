from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.org import SystemUser, UserSession
from app.schemas.token import Token
from app.schemas.user import User
from app.schemas.response import StandardResponse, success, error

router = APIRouter()

@router.post("/login", response_model=StandardResponse[Token])
async def login(
    response: Response,
    db: AsyncSession = Depends(deps.get_async_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """登录接口: 单设备登录控制"""
    # 1. 验证用户
    stmt = select(SystemUser).where(SystemUser.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    # 2. 单设备登录控制: 清除旧会话
    # 设计要求: 清除该账号在 Redis 中的旧会话 (此处先实现数据库层面的清理)
    await db.execute(delete(UserSession).where(UserSession.user_id == user.user_id))
    # 3. 创建 Token
    access_token = security.create_access_token(user.user_id)
    refresh_token = security.create_refresh_token(user.user_id)

    access_payload = security.decode_token(access_token)
    refresh_payload = security.decode_token(refresh_token)

    access_jti = access_payload.get("jti")
    refresh_jti = refresh_payload.get("jti")

    # 4. 持久化会话 (用于 Refresh 和踢人 P7.7)
    # 使用 refresh_jti 作为 session_id
    new_session = UserSession(
        session_id=refresh_jti, 
        user_id=user.user_id,
        refresh_token_hash=security.get_password_hash(refresh_token),
        access_jti=access_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_session)
    await db.commit()

    # 5. 设置 HttpOnly Cookie (存放 Refresh Token)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        samesite="lax",
        secure=not settings.DEBUG # 生产环境开启 Secure
    )

    return success(data={"access_token": access_token, "token_type": "bearer"})

@router.get("/me", response_model=StandardResponse[User])
async def read_user_me(
    current_user: SystemUser = Depends(deps.get_current_user),
) -> Any:
    """获取当前用户信息"""
    # 转换为 User 响应模型，确保 ID 映射正确
    return success(data=current_user)

@router.post("/refresh", response_model=StandardResponse[Token])
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(deps.get_async_db)
) -> Any:
    """无感续期: 使用 Cookie 中的 Refresh Token 换发 Access Token"""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    try:
        payload = security.decode_token(refresh_token)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # 验证数据库中的会话
    stmt = select(UserSession).where(UserSession.user_id == int(user_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session or not security.verify_password(refresh_token, session.refresh_token_hash):
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # 签发新 Access Token
    access_token = security.create_access_token(user_id)
    return success(data={"access_token": access_token, "token_type": "bearer"})

@router.post("/logout", response_model=StandardResponse)
async def logout(
    response: Response,
    current_user: SystemUser = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_async_db)
) -> Any:
    """登出"""
    await db.execute(delete(UserSession).where(UserSession.user_id == current_user.user_id))
    await db.commit()
    response.delete_cookie("refresh_token")
    return success(message="Successfully logged out")
