from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_async_db
from app.models.user import User, Department
from app.api.dependencies import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.security import pwd_context

router = APIRouter()

class UserBase(BaseModel):
    username: str
    dept_id: Optional[int] = None
    role_level: int = 1
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    dept_id: Optional[int] = None
    role_level: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserOut(UserBase):
    user_id: int
    created_at: datetime
    model_config = {"from_attributes": True}

@router.get("/", response_model=List[UserOut])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.execute(select(User))
    return result.scalars().all()

@router.post("/", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Admin only")
    
    # 检查用户名重复
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
        dept_id=payload.dept_id,
        role_level=payload.role_level,
        is_active=payload.is_active
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Admin only")
        
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404)
        
    if payload.dept_id is not None: user.dept_id = payload.dept_id
    if payload.role_level is not None: user.role_level = payload.role_level
    if payload.is_active is not None: user.is_active = payload.is_active
    if payload.password: user.password_hash = pwd_context.hash(payload.password)
    
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Admin only")
        
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404)
        
    await db.delete(user)
    await db.commit()
    return {"status": "success"}
