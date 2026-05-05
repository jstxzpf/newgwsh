from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.knowledge import KnowledgeBaseHierarchy
from app.models.enums import KBTier, DataSecurityLevel
from app.api.dependencies import get_current_user
from app.services.knowledge_service import KnowledgeService
import time
from typing import List, Dict

router = APIRouter()

@router.get("/hierarchy")
async def get_hierarchy(
    tier: KBTier = Query(KBTier.PERSONAL), 
    current_user: SystemUser = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    query = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False, KnowledgeBaseHierarchy.kb_tier == tier)
    
    # 权限隔离 §八
    if tier == KBTier.PERSONAL:
        query = query.where(KnowledgeBaseHierarchy.owner_id == current_user.user_id)
    elif tier == KBTier.DEPT:
        query = query.where(KnowledgeBaseHierarchy.dept_id == current_user.dept_id)
    # BASE 允许全部访问 §二.3
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # 构建嵌套树结构 (§8 契约)
    nodes: Dict[int, dict] = {}
    root_nodes: List[dict] = []
    
    for item in items:
        node = {
            "kb_id": item.kb_id, 
            "kb_name": item.kb_name, 
            "kb_type": item.kb_type, 
            "security_level": item.security_level,
            "parse_status": item.parse_status,
            "children": []
        }
        nodes[item.kb_id] = node
        
    for item in items:
        if item.parent_id and item.parent_id in nodes:
            nodes[item.parent_id]["children"].append(nodes[item.kb_id])
        else:
            root_nodes.append(nodes[item.kb_id])
            
    return {
        "code": 200, 
        "message": "success", 
        "data": root_nodes
    }

@router.get("/snapshot-version")
async def get_snapshot_version(current_user: SystemUser = Depends(get_current_user)):
    return {"code": 200, "message": "success", "data": {"snapshot_version": int(time.time())}}

@router.post("/upload")
async def upload_file(
    parent_id: int | None = Form(None),
    kb_tier: KBTier = Form(KBTier.PERSONAL),
    security_level: DataSecurityLevel = Form(DataSecurityLevel.GENERAL),
    file: UploadFile = File(...),
    current_user: SystemUser = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    if kb_tier == KBTier.BASE and current_user.role_level < 99:
        raise BusinessException(403, "无权写入基础库")
    if kb_tier == KBTier.DEPT and current_user.role_level < 5:
        raise BusinessException(403, "无权写入科室库")

    content = await file.read()
    kb_id = await KnowledgeService.handle_upload(
        db, file.filename, content, parent_id, kb_tier, security_level, current_user.user_id, current_user.dept_id
    )
    await db.commit()
    
    from app.tasks.worker import process_parse_task
    process_parse_task.delay(kb_id)
    
    return {"code": 200, "message": "success", "data": {"kb_id": kb_id}}

@router.put("/{kb_id}")
async def replace_kb_node(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == kb_id).with_for_update())
    node = result.scalars().first()
    if not node:
        raise BusinessException(404, "节点不存在")
    
    if node.owner_id != current_user.user_id and current_user.role_level < 99:
        raise BusinessException(403, "无权修改他人资产")

    content = await file.read()
    new_kb_id = await KnowledgeService.handle_upload(
        db, file.filename, content, node.parent_id, node.kb_tier, node.security_level, current_user.user_id, current_user.dept_id
    )
    
    node.is_deleted = True
    await db.commit()
    
    from app.tasks.worker import process_parse_task
    process_parse_task.delay(new_kb_id)
    
    return {"code": 200, "message": "success", "data": {"kb_id": new_kb_id}}

@router.delete("/{kb_id}")
async def delete_kb_node(kb_id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await KnowledgeService.delete_node(db, kb_id, current_user.user_id)
    return {"code": 200, "message": "success", "data": None}

from app.core.exceptions import BusinessException