from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.system import UserNotification
from app.schemas.notification import NotificationReadRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("")
async def get_notifications(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    is_read: bool = Query(None),
    current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    query = select(UserNotification).where(UserNotification.user_id == current_user.user_id)
    if is_read is not None:
        query = query.where(UserNotification.is_read == is_read)
        
    query = query.order_by(UserNotification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # 简化的分页返回
    return {"code": 200, "message": "success", "data": {
        "total": len(items), # 实际应为 count 查出
        "items": [{
            "notification_id": item.notification_id,
            "doc_id": item.doc_id,
            "type": item.type,
            "content": item.content,
            "is_read": item.is_read
        } for item in items]
    }}

@router.get("/unread-count")
async def get_unread_count(current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserNotification).where(UserNotification.user_id == current_user.user_id, UserNotification.is_read == False))
    count = len(result.scalars().all()) # 简化为查询出 list 求长度
    return {"code": 200, "message": "success", "data": {"unread_count": count}}

@router.post("/{id}/read")
async def mark_read(id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(UserNotification).where(UserNotification.notification_id == id, UserNotification.user_id == current_user.user_id).values(is_read=True))
    await db.commit()
    return {"code": 200, "message": "success", "data": None}

@router.post("/read-all")
async def mark_all_read(current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(UserNotification).where(UserNotification.user_id == current_user.user_id).values(is_read=True))
    await db.commit()
    return {"code": 200, "message": "success", "data": None}