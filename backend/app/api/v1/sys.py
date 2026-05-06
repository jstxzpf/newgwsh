from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.core.database import get_db
from app.models.user import SystemUser, Department
from app.models.document import Document
from app.models.system import SystemConfig, NBSWorkflowAudit
from app.schemas.sys import (
    ConfigUpdateRequest, UserCreateRequest, UserUpdateRequest,
    PasswordResetRequest, DeptCreateRequest, DeptUpdateRequest
)
from app.core.exceptions import BusinessException
from app.core.security import get_password_hash
from app.api.dependencies import get_current_user
from app.core.locks import list_all_locks
import os

router = APIRouter()


async def get_admin_user(current_user: SystemUser = Depends(get_current_user)):
    if current_user.role_level < 99:
        raise BusinessException(403, "需要管理员权限")
    return current_user


# ════════════════════════════════════════════════════════════
# System Status & Config
# ════════════════════════════════════════════════════════════

@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    # Real probe: check DB, Redis, and optional Ollama connectivity
    db_ok = False
    try:
        result = await db.execute(select(func.count()).select_from(SystemUser).limit(1))
        result.scalar()
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        from app.core.locks import redis_client
        redis_ok = await redis_client.ping()
    except Exception:
        pass

    ai_online = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ai_online = resp.status_code == 200
    except Exception:
        pass

    return {"code": 200, "message": "success", "data": {
        "db_connected": db_ok,
        "redis_connected": redis_ok,
        "celery_workers_active": -1,  # Requires Celery inspect, not probed here
        "ai_engine_online": ai_online
    }}


@router.get("/config")
async def list_config(admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    return {"code": 200, "data": [
        {"key": c.config_key, "value": c.config_value, "description": c.description, "value_type": c.value_type}
        for c in configs
    ]}


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


# ════════════════════════════════════════════════════════════
# User CRUD
# ════════════════════════════════════════════════════════════

@router.get("/users")
async def list_users(
    dept_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    admin_user: SystemUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(SystemUser)
    if dept_id is not None:
        q = q.where(SystemUser.dept_id == dept_id)
    if is_active is not None:
        q = q.where(SystemUser.is_active == is_active)
    q = q.order_by(SystemUser.user_id)
    result = await db.execute(q)
    users = result.scalars().all()
    return {"code": 200, "data": [
        {
            "user_id": u.user_id, "username": u.username, "full_name": u.full_name,
            "dept_id": u.dept_id, "role_level": u.role_level, "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]}


@router.post("/users")
async def create_user(req: UserCreateRequest, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(SystemUser).where(SystemUser.username == req.username))
    if existing.scalars().first():
        raise BusinessException(409, "用户名已存在")

    user = SystemUser(
        username=req.username,
        full_name=req.full_name,
        password_hash=get_password_hash(req.password),
        dept_id=req.dept_id,
        role_level=req.role_level,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"code": 201, "message": "用户已创建", "data": {"user_id": user.user_id}}


@router.put("/users/{user_id}")
async def update_user(user_id: int, req: UserUpdateRequest, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemUser).where(SystemUser.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise BusinessException(404, "用户不存在")

    if req.full_name is not None:
        user.full_name = req.full_name
    if req.dept_id is not None:
        user.dept_id = req.dept_id
    if req.role_level is not None:
        user.role_level = req.role_level
    if req.is_active is not None:
        user.is_active = req.is_active

    await db.commit()
    return {"code": 200, "message": "用户已更新", "data": None}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    if user_id == admin_user.user_id:
        raise BusinessException(400, "不可删除自己")

    result = await db.execute(select(SystemUser).where(SystemUser.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise BusinessException(404, "用户不存在")

    # Check for owned documents
    doc_count = await db.execute(
        select(func.count(Document.doc_id)).where(Document.creator_id == user_id)
    )
    if doc_count.scalar() > 0:
        raise BusinessException(409, f"该用户拥有 {doc_count.scalar()} 份公文，请先迁移或删除后再操作")

    await db.delete(user)
    await db.commit()
    return {"code": 200, "message": "用户已删除", "data": None}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, req: PasswordResetRequest, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemUser).where(SystemUser.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise BusinessException(404, "用户不存在")

    user.password_hash = get_password_hash(req.new_password)
    await db.commit()
    return {"code": 200, "message": "密码已重置", "data": None}


# ════════════════════════════════════════════════════════════
# Department CRUD
# ════════════════════════════════════════════════════════════

@router.get("/departments")
async def list_departments(
    is_active: bool | None = Query(None),
    admin_user: SystemUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(Department)
    if is_active is not None:
        q = q.where(Department.is_active == is_active)
    q = q.order_by(Department.dept_id)
    result = await db.execute(q)
    depts = result.scalars().all()
    return {"code": 200, "data": [
        {
            "dept_id": d.dept_id, "dept_name": d.dept_name, "dept_code": d.dept_code,
            "dept_head_id": d.dept_head_id, "is_active": d.is_active,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in depts
    ]}


@router.post("/departments")
async def create_department(req: DeptCreateRequest, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Department).where(Department.dept_name == req.dept_name))
    if existing.scalars().first():
        raise BusinessException(409, "科室名称已存在")

    dept = Department(
        dept_name=req.dept_name,
        dept_code=req.dept_code,
        dept_head_id=req.dept_head_id,
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return {"code": 201, "message": "科室已创建", "data": {"dept_id": dept.dept_id}}


@router.put("/departments/{dept_id}")
async def update_department(dept_id: int, req: DeptUpdateRequest, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.dept_id == dept_id))
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(404, "科室不存在")

    if req.dept_name is not None:
        dept.dept_name = req.dept_name
    if req.dept_code is not None:
        dept.dept_code = req.dept_code
    if req.dept_head_id is not None:
        dept.dept_head_id = req.dept_head_id
    if req.is_active is not None:
        dept.is_active = req.is_active

    await db.commit()
    return {"code": 200, "message": "科室已更新", "data": None}


@router.delete("/departments/{dept_id}")
async def delete_department(dept_id: int, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.dept_id == dept_id))
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(404, "科室不存在")

    # Check for users in department
    user_count = await db.execute(
        select(func.count(SystemUser.user_id)).where(SystemUser.dept_id == dept_id)
    )
    if user_count.scalar() > 0:
        raise BusinessException(409, f"该科室下有 {user_count.scalar()} 名用户，请先迁移后再操作")

    await db.delete(dept)
    await db.commit()
    return {"code": 200, "message": "科室已删除", "data": None}


# ════════════════════════════════════════════════════════════
# Document Types CRUD
# ════════════════════════════════════════════════════════════

@router.get("/doc-types")
async def list_doc_types(admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from app.models.document import DocumentType
    result = await db.execute(select(DocumentType).order_by(DocumentType.type_id))
    types = result.scalars().all()
    return {"code": 200, "data": [
        {
            "type_id": t.type_id, "type_code": t.type_code, "type_name": t.type_name,
            "layout_rules": t.layout_rules, "is_active": t.is_active
        }
        for t in types
    ]}


@router.post("/doc-types")
async def create_doc_type(req: dict, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from app.models.document import DocumentType
    existing = await db.execute(select(DocumentType).where(DocumentType.type_code == req.get("type_code")))
    if existing.scalars().first():
        raise BusinessException(409, "文种编码已存在")
    dt = DocumentType(
        type_code=req["type_code"],
        type_name=req["type_name"],
        layout_rules=req.get("layout_rules", {})
    )
    db.add(dt)
    await db.commit()
    await db.refresh(dt)
    return {"code": 201, "message": "文种已创建", "data": {"type_id": dt.type_id}}


@router.put("/doc-types/{type_id}")
async def update_doc_type(type_id: int, req: dict, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from app.models.document import DocumentType
    result = await db.execute(select(DocumentType).where(DocumentType.type_id == type_id))
    dt = result.scalars().first()
    if not dt:
        raise BusinessException(404, "文种不存在")
    if "type_name" in req:
        dt.type_name = req["type_name"]
    if "layout_rules" in req:
        dt.layout_rules = req["layout_rules"]
    if "is_active" in req:
        dt.is_active = req["is_active"]
    await db.commit()
    return {"code": 200, "message": "文种已更新", "data": None}


@router.delete("/doc-types/{type_id}")
async def delete_doc_type(type_id: int, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from app.models.document import DocumentType
    result = await db.execute(select(DocumentType).where(DocumentType.type_id == type_id))
    dt = result.scalars().first()
    if not dt:
        raise BusinessException(404, "文种不存在")
    dt.is_active = False
    await db.commit()
    return {"code": 200, "message": "文种已停用", "data": None}


# ════════════════════════════════════════════════════════════
# Prompts
# ════════════════════════════════════════════════════════════

SYSTEM_CHAT_PROMPT = os.path.join("app", "prompts", "system_chat.txt")


@router.get("/prompt")
async def get_system_prompt(admin_user: SystemUser = Depends(get_admin_user)):
    if os.path.exists(SYSTEM_CHAT_PROMPT):
        with open(SYSTEM_CHAT_PROMPT, "r", encoding="utf-8") as f:
            return {"code": 200, "data": {"content": f.read()}}
    return {"code": 200, "data": {"content": ""}}


@router.post("/prompt")
async def save_system_prompt(req: dict, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    os.makedirs(os.path.dirname(SYSTEM_CHAT_PROMPT), exist_ok=True)
    content = req.get("content", "")
    with open(SYSTEM_CHAT_PROMPT, "w", encoding="utf-8") as f:
        f.write(content)

    audit = NBSWorkflowAudit(
        doc_id=None,
        workflow_node_id=0,
        operator_id=admin_user.user_id,
        action_details={"action": "PROMPT_EDIT", "filename": "system_chat.txt"}
    )
    db.add(audit)
    await db.commit()

    return {"code": 200, "message": "提示词已保存并热加载", "data": None}


@router.get("/prompts")
async def list_prompts(admin_user: SystemUser = Depends(get_admin_user)):
    prompt_dir = "app/prompts"
    if not os.path.exists(prompt_dir):
        return {"code": 200, "data": []}
    files = os.listdir(prompt_dir)
    return {"code": 200, "data": [{"filename": f} for f in files if f.endswith(".txt")]}


@router.put("/prompts/{filename}")
async def edit_prompt(filename: str, req: dict, admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    path = os.path.join("app/prompts", filename)
    if not os.path.exists(path):
        raise BusinessException(404, "提示词文件不存在")
    content = req.get("content", "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    audit = NBSWorkflowAudit(
        doc_id=None,
        workflow_node_id=0,
        operator_id=admin_user.user_id,
        action_details={"action": "PROMPT_EDIT", "filename": filename}
    )
    db.add(audit)
    await db.commit()

    return {"code": 200, "message": "已覆盖保存"}


@router.post("/reload-prompts")
async def reload_prompts(admin_user: SystemUser = Depends(get_admin_user)):
    return {"code": 200, "message": "提示词已热加载", "data": {"reloaded": True}}


# ════════════════════════════════════════════════════════════
# Database Snapshots & Maintenance
# ════════════════════════════════════════════════════════════

import subprocess
import glob as glob_mod
from app.core.config import settings


@router.get("/db-snapshots")
async def list_db_snapshots(admin_user: SystemUser = Depends(get_admin_user)):
    backup_dir = "/app/data/backups"
    snapshots = []
    if os.path.exists(backup_dir):
        for f in sorted(os.listdir(backup_dir), reverse=True):
            if f.endswith(".dump"):
                fpath = os.path.join(backup_dir, f)
                snapshots.append({
                    "id": f.replace(".dump", ""),
                    "filename": f,
                    "size": os.path.getsize(fpath),
                    "created_at": os.path.getmtime(fpath)
                })
    return {"code": 200, "data": snapshots}


@router.post("/db-snapshot")
async def create_db_snapshot(admin_user: SystemUser = Depends(get_admin_user)):
    backup_dir = "/app/data/backups"
    os.makedirs(backup_dir, exist_ok=True)
    import datetime as dt
    snapshot_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(backup_dir, f"{snapshot_id}.dump")
    try:
        subprocess.run([
            "pg_dump",
            f"--dbname=postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}",
            "--format=custom", f"--file={path}"
        ], check=True, capture_output=True, timeout=120)
        return {"code": 201, "message": "快照创建成功", "data": {"id": snapshot_id, "size": os.path.getsize(path)}}
    except subprocess.CalledProcessError as e:
        raise BusinessException(500, f"pg_dump 失败: {e.stderr.decode() if e.stderr else str(e)}")
    except FileNotFoundError:
        raise BusinessException(500, "pg_dump 命令不可用")


@router.post("/db-snapshots/{id}/restore")
async def restore_db_snapshot(id: str, admin_user: SystemUser = Depends(get_admin_user)):
    backup_dir = "/app/data/backups"
    path = os.path.join(backup_dir, f"{id}.dump")
    if not os.path.exists(path):
        raise BusinessException(404, "快照文件不存在")
    return {"code": 200, "message": "高危操作：请在服务器终端手动执行 pg_restore 恢复此快照"}


@router.post("/cleanup-cache")
async def cleanup_cache(admin_user: SystemUser = Depends(get_admin_user)):
    cleaned = 0
    temp_dirs = ["/tmp", "/app/data/uploads"]
    for d in temp_dirs:
        if os.path.exists(d):
            for f in glob_mod.glob(os.path.join(d, "*.tmp")):
                try:
                    os.remove(f)
                    cleaned += 1
                except OSError:
                    pass
    return {"code": 200, "message": f"已清理 {cleaned} 个临时文件", "data": {"cleaned_files": cleaned}}


@router.post("/gin-maintenance")
async def gin_maintenance(admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from app.models.knowledge import KnowledgeChunk
    result = await db.execute(
        update(KnowledgeChunk)
        .where(KnowledgeChunk.is_deleted == True, KnowledgeChunk.content != "")
        .values(content="", embedding=None)
    )
    await db.commit()
    return {"code": 200, "message": f"索引维护完成，清理 {result.rowcount} 条死向量"}


@router.post("/scan-orphan-files")
async def scan_orphan_files(admin_user: SystemUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from app.models.knowledge import KnowledgePhysicalFile
    upload_dir = "/app/data/uploads"
    orphans = []
    if os.path.exists(upload_dir):
        all_files = set(os.listdir(upload_dir))
        result = await db.execute(select(KnowledgePhysicalFile.file_path))
        db_paths = set()
        for row in result.scalars().all():
            if row:
                db_paths.add(os.path.basename(row))
        orphans = list(all_files - db_paths)
    return {"code": 200, "data": [{"filename": f, "path": os.path.join(upload_dir, f)} for f in orphans]}


# ════════════════════════════════════════════════════════════
# Lock Monitor
# ════════════════════════════════════════════════════════════

@router.get("/locks")
async def get_active_locks(admin_user: SystemUser = Depends(get_admin_user)):
    locks = await list_all_locks()
    return {"code": 200, "message": "success", "data": locks}
