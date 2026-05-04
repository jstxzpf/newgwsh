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
    
    access_token = create_access_token(subject=user.user_id)
    refresh_token = create_refresh_token(subject=user.user_id)
    
    # 写入新会话
    await AuthService.create_session(db, user.user_id, get_password_hash(refresh_token))
    await db.commit()
    
    # Refresh Token 存放于 HttpOnly Cookie
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=7*24*3600, samesite="lax")
    return {"code": 200, "message": "success", "data": {"access_token": access_token, "token_type": "bearer"}}

@router.get("/me", response_model=dict)
async def get_me(current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.user import Department
    result = await db.execute(
        select(SystemUser, Department.dept_name)
        .outerjoin(Department, SystemUser.dept_id == Department.dept_id)
        .where(SystemUser.user_id == current_user.user_id)
    )
    row = result.first()
    
    data = UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        full_name=current_user.full_name,
        role_level=current_user.role_level,
        dept_id=current_user.dept_id,
        department_name=row[1] if row else None
    )
    return {"code": 200, "message": "success", "data": data.model_dump()}

@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise BusinessException(401, "会话已过期，请重新登录")
    
    try:
        payload = decode_token(refresh_token)
        user_id = int(payload.get("sub"))
    except:
        raise BusinessException(401, "无效的凭证")
    
    # 换发新 Token
    access_token = create_access_token(subject=user_id)
    return {"code": 200, "message": "success", "data": {"access_token": access_token}}

@router.post("/logout")
async def logout(current_user: SystemUser = Depends(get_current_user), response: Response, db: AsyncSession = Depends(get_db)):
    # 清除会话记录（契约 §1）
    await AuthService.clear_user_sessions(db, current_user.user_id)
    await db.commit()
    response.delete_cookie("refresh_token")
    return {"code": 200, "message": "success", "data": None}