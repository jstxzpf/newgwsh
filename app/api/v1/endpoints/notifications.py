from typing import Any, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.org import SystemUser
from app.models.audit import UserNotification
from app.schemas.response import StandardResponse, success, error

router = APIRouter()

@router.get("/", response_model=StandardResponse)
async def list_notifications(
    is_read: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取通知列表 (P11)"""
    stmt = select(UserNotification).where(UserNotification.user_id == current_user.user_id)
    if is_read is not None:
        stmt = stmt.where(UserNotification.is_read == is_read)
        
    stmt = stmt.order_by(UserNotification.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    return success(data={"items": items, "total": len(items)})

@router.get("/unread-count", response_model=StandardResponse)
async def get_unread_count(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取未读通知数"""
    from sqlalchemy import func
    stmt = select(func.count(UserNotification.notification_id)).where(
        UserNotification.user_id == current_user.user_id,
        UserNotification.is_read == False
    )
    count = (await db.execute(stmt)).scalar()
    return success(data={"unread_count": count})

@router.post("/{notification_id}/read", response_model=StandardResponse)
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """标记单条已读"""
    notification = await db.get(UserNotification, notification_id)
    if not notification or notification.user_id != current_user.user_id:
        return error(code=404, message="Notification not found")
        
    notification.is_read = True
    await db.commit()
    return success(message="Marked as read")

@router.post("/read-all", response_model=StandardResponse)
async def mark_all_as_read(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """一键已读全部"""
    from sqlalchemy import update
    stmt = update(UserNotification).where(
        UserNotification.user_id == current_user.user_id,
        UserNotification.is_read == False
    ).values(is_read=True)
    await db.execute(stmt)
    await db.commit()
    return success(message="All notifications marked as read")
