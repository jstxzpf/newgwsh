from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser, UserSession
from app.schemas.auth import LoginRequest, LoginResponse, UserInfoResponse
from app.core.security import verify_password, create_access_token, create_refresh_token, get_password_hash
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import uuid
from datetime import datetime, timedelta, timezone

router = APIRouter()

@router.post("/login", response_model=dict)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemUser).where(SystemUser.username == req.username))
    user = result.scalars().first()
    if not user or not verify_password(req.password, user.password_hash):
        raise BusinessException(401, "用户名或密码错误")
    if not user.is_active:
        raise BusinessException(403, "账号已被停用")
        
    # 清除旧会话
    from sqlalchemy import delete
    await db.execute(delete(UserSession).where(UserSession.user_id == user.user_id))
    
    access_token = create_access_token(subject=user.user_id)
    refresh_token = create_refresh_token(subject=user.user_id)
    
    # 写入新会话
    session_id = str(uuid.uuid4())
    new_session = UserSession(
        session_id=session_id,
        user_id=user.user_id,
        refresh_token_hash=get_password_hash(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(new_session)
    await db.commit()
    
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=7*24*3600)
    return {"code": 200, "message": "success", "data": {"access_token": access_token, "token_type": "bearer"}}

@router.get("/me", response_model=dict)
async def get_me(current_user: SystemUser = Depends(get_current_user)):
    data = UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        full_name=current_user.full_name,
        role_level=current_user.role_level,
        dept_id=current_user.dept_id
    )
    return {"code": 200, "message": "success", "data": data.model_dump()}