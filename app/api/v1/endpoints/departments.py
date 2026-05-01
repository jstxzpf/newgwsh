from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.org import SystemUser, Department
from app.schemas.response import StandardResponse, success, error

router = APIRouter()

@router.get("/", response_model=StandardResponse)
async def list_departments(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """科室管理: 列表查询"""
    stmt = select(Department)
    result = await db.execute(stmt)
    return success(data=result.scalars().all())

@router.post("/", response_model=StandardResponse)
async def create_department(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user),
    dept_name: str = Body(...),
    dept_code: str = Body(...),
    dept_head_id: Optional[int] = Body(None)
) -> Any:
    """新建科室"""
    dept = Department(
        dept_name=dept_name,
        dept_code=dept_code,
        dept_head_id=dept_head_id
    )
    db.add(dept)
    await db.commit()
    return success(data={"dept_id": dept.dept_id})

@router.patch("/{dept_id}/toggle-active", response_model=StandardResponse)
async def toggle_dept_active(
    dept_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """科室启停管理"""
    dept = await db.get(Department, dept_id)
    if not dept:
        return error(code=404, message="Department not found")
    dept.is_active = not dept.is_active
    await db.commit()
    return success(message=f"Department status toggled to {dept.is_active}")
