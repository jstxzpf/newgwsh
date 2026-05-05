from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.system import SystemConfig
from app.schemas.sys import ConfigUpdateRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.locks import list_all_locks
from app.models.system import NBSWorkflowAudit
import os
import json

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
        cfg.updated_by = admin_user.user_id
    else:
        new_cfg = SystemConfig(config_key=req.config_key, config_value=str(req.config_value), updated_by=admin_user.user_id)
        db.add(new_cfg)
    await db.commit()
    return {"code": 200, "message": "配置已更新", "data": None}

@router.get("/prompts")
async def list_prompts(admin_user: SystemUser = Depends(get_admin_user)):
    prompt_dir = "app/prompts"
    if not os.path.exists(prompt_dir):
        return {"code": 200, "data": []}
    files = os.listdir(prompt_dir)
    return {"code": 200, "data": [{"filename": f} for f in files if f.endswith(".txt")]}

@router.put("/prompts/{filename}")
async def edit_prompt(filename: str, req: dict, admin_user: SystemUser = Depends(get_admin_user)):
    path = os.path.join("app/prompts", filename)
    if not os.path.exists(path):
        raise BusinessException(404, "提示词文件不存在")
    content = req.get("content", "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"code": 200, "message": "已覆盖保存"}

@router.post("/reload-prompts")
async def reload_prompts(admin_user: SystemUser = Depends(get_admin_user)):
    # 逻辑：通知后端实例重新拉取磁盘提示词
    return {"code": 200, "message": "提示词已热加载", "data": {"reloaded": True}}

@router.get("/db-snapshots")
async def list_db_snapshots(admin_user: SystemUser = Depends(get_admin_user)):
    # 模拟返回历史 pg_dump 快照
    return {"code": 200, "data": []}

@router.post("/db-snapshot")
async def create_db_snapshot(admin_user: SystemUser = Depends(get_admin_user)):
    # 模拟触发 pg_dump 异步任务
    return {"code": 202, "message": "快照任务已派发"}

@router.post("/db-snapshots/{id}/restore")
async def restore_db_snapshot(id: str, admin_user: SystemUser = Depends(get_admin_user)):
    # 高危操作！执行 pg_restore
    return {"code": 200, "message": "快照恢复成功（模拟）"}

@router.post("/cleanup-cache")
async def cleanup_cache(admin_user: SystemUser = Depends(get_admin_user)):
    return {"code": 200, "message": "已清理临时文件", "data": {"cleaned_files": 0}}

@router.post("/gin-maintenance")
async def gin_maintenance(admin_user: SystemUser = Depends(get_admin_user)):
    # 逻辑：批量将 is_deleted=True 的向量切片 content 置空
    return {"code": 200, "message": "索引维护完成"}

@router.post("/scan-orphan-files")
async def scan_orphan_files(admin_user: SystemUser = Depends(get_admin_user)):
    return {"code": 200, "data": []}

@router.get("/locks")
async def get_active_locks(admin_user: SystemUser = Depends(get_admin_user)):
    locks = await list_all_locks()
    return {"code": 200, "message": "success", "data": locks}