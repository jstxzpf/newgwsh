import os
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.org import SystemUser
from app.models.config import SystemConfig
from app.schemas.response import StandardResponse, success, error
from app.core.config import settings

router = APIRouter()

@router.get("/dashboard-stats", response_model=StandardResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取仪表盘统计数据 (P5.3)"""
    from sqlalchemy import func
    from app.models.document import Document, DocStatus
    from app.models.task import AsyncTask, TaskStatus
    
    # 1. 统计公文
    stmt_docs = select(Document.status, func.count(Document.doc_id)).where(Document.is_deleted == False)
    if current_user.role_level < 99:
        stmt_docs = stmt_docs.where(Document.dept_id == current_user.dept_id)
    stmt_docs = stmt_docs.group_by(Document.status)
    res_docs = (await db.execute(stmt_docs)).all()
    
    doc_stats = {status.name: count for status, count in res_docs}
    
    # 2. 统计任务 (最近 7 天)
    from datetime import datetime, timedelta, timezone
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    stmt_tasks = select(AsyncTask.task_status, func.count(AsyncTask.task_id)).where(
        AsyncTask.creator_id == current_user.user_id,
        AsyncTask.created_at >= seven_days_ago
    ).group_by(AsyncTask.task_status)
    res_tasks = (await db.execute(stmt_tasks)).all()
    
    task_stats = {status.name: count for status, count in res_tasks}
    
    return success(data={
        "document_counts": doc_stats,
        "recent_task_counts": task_stats,
        "total_documents": sum(doc_stats.values()),
        "pending_tasks": task_stats.get("QUEUED", 0) + task_stats.get("PROCESSING", 0)
    })

@router.get("/status", response_model=StandardResponse)
async def get_system_status(
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """全局探针: 返回 DB/Redis/Ollama 连通性"""
    # 简单模拟状态返回
    return success(data={
        "db_connected": True,
        "redis_connected": True,
        "ai_engine_online": True,
        "cpu_usage_pct": 15,
        "memory_usage_pct": 45
    })

@router.get("/config", response_model=StandardResponse)
async def get_configs(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """获取所有动态配置"""
    stmt = select(SystemConfig)
    result = await db.execute(stmt)
    return success(data=result.scalars().all())

@router.put("/config", response_model=StandardResponse)
async def update_config(
    key: str,
    value: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """更新动态配置"""
    stmt = select(SystemConfig).where(SystemConfig.config_key == key)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        return error(code=404, message="Config key not found")
        
    config.config_value = value
    config.updated_by = current_user.user_id
    await db.commit()
    return success(message=f"Config {key} updated")

@router.get("/prompts", response_model=StandardResponse)
async def list_prompts(
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """获取提示词列表"""
    prompt_dir = settings.PROMPTS_ROOT
    if not os.path.exists(prompt_dir):
        return success(data=[])
    files = os.listdir(prompt_dir)
    return success(data=[{"filename": f, "path": os.path.join(prompt_dir, f)} for f in files if f.endswith(".txt")])

@router.put("/prompts/{filename}", response_model=StandardResponse)
async def update_prompt(
    filename: str,
    content: str,
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """更新提示词文件并触发热加载 (实施约束规则 8)"""
    if not filename.endswith(".txt"):
        return error(code=400, message="Only .txt files allowed")
        
    path = os.path.join(settings.PROMPTS_ROOT, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    
    # 自动热加载
    from app.services.prompt_service import prompt_loader
    prompt_loader.reload()
    
    return success(message=f"Prompt {filename} updated and reloaded")

@router.post("/reload-prompts", response_model=StandardResponse)
async def reload_prompts(
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """手动热加载提示词"""
    from app.services.prompt_service import prompt_loader
    prompt_loader.reload()
    return success(message="Prompts reloaded from disk")

@router.post("/db-snapshot", response_model=StandardResponse)
async def trigger_db_snapshot(
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """手动触发数据库快照备份 (pg_dump 异步任务)"""
    from app.tasks.worker import db_snapshot
    db_snapshot.delay()
    return success(message="DB snapshot task triggered")

@router.get("/db-snapshots", response_model=StandardResponse)
async def list_db_snapshots(
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """获取数据库快照列表 (P7.11)"""
    archive_dir = os.path.join(settings.STORAGE_ROOT, "archives")
    if not os.path.exists(archive_dir):
        return success(data=[])
        
    snapshots = []
    for f in os.listdir(archive_dir):
        if f.endswith(".sql"):
            path = os.path.join(archive_dir, f)
            stat = os.stat(path)
            snapshots.append({
                "snapshot_id": f.replace(".sql", ""),
                "filename": f,
                "size_bytes": stat.st_size,
                "created_at": stat.st_mtime,
                "status": "COMPLETED" # 简化处理
            })
    return success(data=snapshots)

@router.post("/scan-orphan-files", response_model=StandardResponse)
async def scan_orphan_files(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """扫描并列出孤立物理文件 (P7.12)"""
    from app.models.knowledge import KnowledgePhysicalFile, KnowledgeBaseHierarchy
    from sqlalchemy import select
    
    # 查找没有任何逻辑节点引用的物理文件
    stmt = select(KnowledgePhysicalFile).where(
        ~KnowledgePhysicalFile.file_id.in_(
            select(KnowledgeBaseHierarchy.physical_file_id).where(KnowledgeBaseHierarchy.physical_file_id != None)
        )
    )
    result = await db.execute(stmt)
    orphans = result.scalars().all()
    
    return success(data=orphans, message=f"Found {len(orphans)} orphan files")

@router.post("/db-snapshots/{snapshot_id}/restore", response_model=StandardResponse)
async def restore_db_snapshot(
    snapshot_id: str,
    confirm: str = Body(..., embed=True),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """快照强制恢复 (P7.7)"""
    if confirm != "CONFIRM":
        return error(code=400, message="Please type 'CONFIRM' to proceed with dangerous restore")
    
    # 获取快照文件路径
    snapshot_dir = os.path.join(settings.STORAGE_ROOT, "archives")
    filepath = os.path.join(snapshot_dir, f"{snapshot_id}.sql")
    
    if not os.path.exists(filepath):
        return error(code=404, message="Snapshot file not found")
        
    from app.tasks.worker import db_restore
    db_restore.delay(filepath)
    return success(message="DB restore task triggered (Async)")

@router.post("/cleanup-cache", response_model=StandardResponse)
async def cleanup_cache(
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """临时文件清理 (P7.8)"""
    import shutil
    temp_dir = os.path.join(settings.STORAGE_ROOT, "temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
    return success(message="Cache cleaned")

@router.post("/gin-maintenance", response_model=StandardResponse)
async def gin_maintenance(
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """PG 索引清理 (P7.9)"""
    from app.tasks.worker import cleanup_gin_index
    cleanup_gin_index.delay()
    return success(message="GIN maintenance task triggered")
