from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.system import UserNotification
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("")
async def get_notifications(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    is_read: bool = Query(None),
    current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    base_query = select(UserNotification).where(UserNotification.user_id == current_user.user_id)
    if is_read is not None:
        base_query = base_query.where(UserNotification.is_read.is_(is_read))

    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = base_query.order_by(UserNotification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"code": 200, "message": "success", "data": {
        "total": total,
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
    result = await db.execute(
        select(func.count()).select_from(
            select(UserNotification).where(
                UserNotification.user_id == current_user.user_id,
                UserNotification.is_read.is_(False)
            ).subquery()
        )
    )
    count = result.scalar() or 0
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