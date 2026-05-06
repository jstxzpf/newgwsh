from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.schemas.auth import LoginRequest, UserInfoResponse
from app.core.security import verify_password, create_access_token, create_refresh_token, get_password_hash, decode_token
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.core.config import settings

router = APIRouter()

@router.post("/login", response_model=dict)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemUser).where(SystemUser.username == req.username))
    user = result.scalars().first()
    if not user or not verify_password(req.password, user.password_hash):
        raise BusinessException(401, "用户名或密码错误")
    if not user.is_active:
        raise BusinessException(403, "账号已被停用")
        
    # 清除旧会话（解耦至 Service，对齐单一设备登录铁律 §五.7）
    await AuthService.clear_user_sessions(db, user.user_id)

    # 创建会话记录（先创建以获取 session_id）
    session_id = await AuthService.create_session(db, user.user_id, get_password_hash("pending"))

    access_token = create_access_token(subject=user.user_id, session_id=session_id)
    refresh_token = create_refresh_token(subject=user.user_id)

    # 回写 refresh_token_hash
    await AuthService.update_session_hash(db, session_id, get_password_hash(refresh_token))
    await db.commit()
    
    # Refresh Token 存放于 HttpOnly Cookie
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token, 
        httponly=True, 
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, 
        samesite="lax"
    )
    return {"code": 200, "message": "success", "data": {"access_token": access_token, "token_type": "bearer"}}

@router.get("/me", response_model=dict)
async def get_me(current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.user import Department
    result = await db.execute(
        select(SystemUser, Department.dept_name, Department.dept_head_id)
        .outerjoin(Department, SystemUser.dept_id == Department.dept_id)
        .where(SystemUser.user_id == current_user.user_id)
    )
    row = result.first()

    is_dept_head = bool(row and row[2] is not None and row[2] == current_user.user_id)

    data = UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        full_name=current_user.full_name,
        role_level=current_user.role_level,
        dept_id=current_user.dept_id,
        department_name=row[1] if row else None,
        is_dept_head=is_dept_head
    )
    return {"code": 200, "message": "success", "data": data.model_dump()}

@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise BusinessException(401, "会话已过期，请重新登录")

    try:
        payload = decode_token(refresh_token_cookie)
        user_id = int(payload.get("sub"))
    except:
        raise BusinessException(401, "无效的凭证")

    # 查找有效会话
    from app.models.user import UserSession
    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc).replace(tzinfo=None)
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.expires_at > now
        )
    )
    session = result.scalars().first()
    if not session:
        raise BusinessException(401, "会话已失效，请重新登录")

    # 换发新 Access Token（携带相同 session_id）
    access_token = create_access_token(subject=user_id, session_id=session.session_id)
    return {"code": 200, "message": "success", "data": {"access_token": access_token}}

@router.post("/logout")
async def logout(response: Response, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 清除会话记录（契约 §1）
    await AuthService.clear_user_sessions(db, current_user.user_id)
    await db.commit()
    response.delete_cookie("refresh_token")
    return {"code": 200, "message": "success", "data": None}