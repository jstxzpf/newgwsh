from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.core.security import create_access_token, create_refresh_token

router = APIRouter()

@router.post("/login")
async def login_access_token(
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # TODO: 实际应验证用户密码，此处 Mock
    user_id = 1
    
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    
    # HttpOnly Cookie 注入 Refresh Token
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token, 
        httponly=True, 
        secure=True, 
        samesite="strict"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_current_user(request: Request):
    # 提取真实 IP (依赖 TrustedHostMiddleware 或 X-Forwarded-For)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
        
    # 返回方案要求的数据结构
    return {
        "user_id": 1,
        "username": "测试科长",
        "dept_id": 1,
        "dept_name": "综合科",
        "role_level": 5,
        "client_ip": client_ip
    }

@router.post("/refresh")
async def refresh_token(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    new_access = create_access_token(subject=1)
    return {"access_token": new_access, "token_type": "bearer"}
