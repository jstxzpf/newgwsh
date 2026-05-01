from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.org import SystemUser, Department
from app.schemas.response import StandardResponse, success, error
from app.core import security

router = APIRouter()

@router.get("/", response_model=StandardResponse)
async def list_users(
    dept_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """用户管理: 列表查询"""
    stmt = select(SystemUser)
    if dept_id:
        stmt = stmt.where(SystemUser.dept_id == dept_id)
    result = await db.execute(stmt)
    return success(data=result.scalars().all())

@router.post("/", response_model=StandardResponse)
async def create_user(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user),
    username: str = Body(...),
    full_name: str = Body(...),
    password: str = Body(...),
    dept_id: int = Body(...),
    role_level: int = Body(1)
) -> Any:
    """新建用户"""
    hashed_pw = security.get_password_hash(password)
    user = SystemUser(
        username=username,
        full_name=full_name,
        password_hash=hashed_pw,
        dept_id=dept_id,
        role_level=role_level
    )
    db.add(user)
    await db.commit()
    return success(data={"user_id": user.user_id})

@router.patch("/{user_id}/toggle-active", response_model=StandardResponse)
async def toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """启用/停用账号 (P6.1)"""
    user = await db.get(SystemUser, user_id)
    if not user:
        return error(code=404, message="User not found")
    user.is_active = not user.is_active
    await db.commit()
    return success(message=f"User status toggled to {user.is_active}")
