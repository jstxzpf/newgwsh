from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_async_db
from app.core.security import create_access_token, create_refresh_token, pwd_context, ALGORITHM
from app.models.user import User, UserSession, Department
from app.core.config import settings
from app.api.dependencies import get_current_user
from jose import jwt, JWTError
import hashlib
import uuid
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/login")
async def login_access_token(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # ... (login remains same)
    stmt = select(User).where(User.username == form_data.username, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    user_id = user.user_id
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    
    session_id = str(uuid.uuid4())
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    new_session = UserSession(
        session_id=session_id,
        user_id=user_id,
        refresh_token_hash=token_hash,
        device_info=request.headers.get("User-Agent", "unknown"),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(new_session)
    await db.commit()
    
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token, 
        httponly=True, 
        secure=True, 
        samesite="strict",
        max_age=7 * 24 * 60 * 60
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_my_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    # 获取部门名称
    dept_name = "业务科室"
    if current_user.dept_id:
        res = await db.execute(select(Department).where(Department.dept_id == current_user.dept_id))
        dept = res.scalars().first()
        if dept:
            dept_name = dept.dept_name
        
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "dept_id": current_user.dept_id,
        "dept_name": dept_name,
        "role_level": current_user.role_level,
        "client_ip": client_ip
    }

@router.post("/refresh")
async def refresh_token(
    request: Request, 
    response: Response,
    db: AsyncSession = Depends(get_async_db)
):
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    try:
        payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
             raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    stmt = select(UserSession).where(
        UserSession.refresh_token_hash == token_hash,
        UserSession.expires_at > datetime.utcnow()
    )
    result = await db.execute(stmt)
    old_session = result.scalars().first()

    if not old_session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    # Token 轮换：删除旧 Session，签发新 Pair
    await db.delete(old_session)
    
    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)
    
    new_session = UserSession(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        refresh_token_hash=hashlib.sha256(new_refresh_token.encode()).hexdigest(),
        device_info=request.headers.get("User-Agent", "unknown"),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(new_session)
    await db.commit()
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60
    )
    
    return {"access_token": new_access_token, "token_type": "bearer"}
