from fastapi import APIRouter, Depends, HTTPException
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

@router.get("/audit")
async def list_audit_logs(
    doc_id: str | None = None,
    operator_id: int | None = None,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    admin_user: SystemUser = Depends(get_admin_user)
):
    query = select(NBSWorkflowAudit).order_by(NBSWorkflowAudit.created_at.desc())
    if doc_id:
        query = query.where(NBSWorkflowAudit.doc_id == doc_id)
    if operator_id:
        query = query.where(NBSWorkflowAudit.operator_id == operator_id)
    
    res = await db.execute(query.limit(50).offset((page-1)*50))
    items = res.scalars().all()
    return {"code": 200, "message": "success", "data": [
        {
            "audit_id": i.audit_id,
            "doc_id": i.doc_id,
            "node": i.workflow_node_id,
            "operator": i.operator_id,
            "details": i.action_details,
            "time": i.created_at
        } for i in items
    ]}

@router.get("/locks")
async def get_active_locks(admin_user: SystemUser = Depends(get_admin_user)):
    locks = await list_all_locks()
    return {"code": 200, "message": "success", "data": locks}

@router.get("/prompt")
async def get_system_prompt(admin_user: SystemUser = Depends(get_admin_user)):
    path = os.path.join(os.path.dirname(__file__), "../../prompts/system_chat.txt")
    if not os.path.exists(path):
        return {"code": 200, "data": {"content": ""}}
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"code": 200, "data": {"content": content}}

@router.post("/prompt")
async def save_system_prompt(req: dict, admin_user: SystemUser = Depends(get_admin_user)):
    content = req.get("content", "")
    path = os.path.join(os.path.dirname(__file__), "../../prompts/system_chat.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"code": 200, "message": "Prompt 已保存并实时生效"}