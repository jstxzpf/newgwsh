from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.org import SystemUser
from app.models.config import DocumentType
from app.schemas.response import StandardResponse, success, error

router = APIRouter()

@router.get("/", response_model=StandardResponse)
async def list_doc_types(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """文种管理: 列表查询"""
    stmt = select(DocumentType)
    result = await db.execute(stmt)
    return success(data=result.scalars().all())

@router.post("/", response_model=StandardResponse)
async def create_doc_type(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user),
    type_code: str = Body(...),
    type_name: str = Body(...),
    layout_rules: dict = Body({})
) -> Any:
    """新建文种"""
    doc_type = DocumentType(
        type_code=type_code,
        type_name=type_name,
        layout_rules=layout_rules
    )
    db.add(doc_type)
    await db.commit()
    return success(data={"type_id": doc_type.type_id})

@router.patch("/{type_id}/toggle-active", response_model=StandardResponse)
async def toggle_doc_type_active(
    type_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """文种启停管理"""
    doc_type = await db.get(DocumentType, type_id)
    if not doc_type:
        return error(code=404, message="DocumentType not found")
    doc_type.is_active = not doc_type.is_active
    await db.commit()
    return success(message=f"DocumentType status toggled to {doc_type.is_active}")
