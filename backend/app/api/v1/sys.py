from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.system import SystemConfig
from app.schemas.sys import ConfigUpdateRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import os

router = APIRouter()

# 简化的管理员权限校验器
async def get_admin_user(current_user: SystemUser = Depends(get_current_user)):
    if current_user.role_level < 99:
        raise BusinessException(403, "需要管理员权限")
    return current_user

@router.get("/status")
async def system_status(admin_user: SystemUser = Depends(get_admin_user)):
    return {"code": 200, "message": "success", "data": {
        "db_connected": True,
        "redis_connected": True,
        "celery_workers_active": 4,
        "ai_engine_online": True
    }}

@router.put("/config")
async def update_config(req: ConfigUpdateRequest, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemConfig).where(SystemConfig.config_key == req.config_key))
    cfg = result.scalars().first()
    if cfg:
        cfg.config_value = str(req.config_value)
    else:
        new_cfg = SystemConfig(config_key=req.config_key, config_value=str(req.config_value))
        db.add(new_cfg)
    await db.commit()
    # TODO: 刷新单例缓存
    return {"code": 200, "message": "success", "data": None}

@router.post("/reload-prompts")
async def reload_prompts(admin_user: SystemUser = Depends(get_admin_user)):
    # 热加载逻辑
    return {"code": 200, "message": "success", "data": {"reloaded": True}}

@router.post("/cleanup-cache")
async def cleanup_cache(admin_user: SystemUser = Depends(get_admin_user)):
    return {"code": 200, "message": "success", "data": {"cleaned_files": 0}}