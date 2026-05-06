from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgePhysicalFile
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
async def get_snapshot_version(current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(func.max(KnowledgeBaseHierarchy.updated_at)).where(
            KnowledgeBaseHierarchy.is_deleted == False
        )
    )
    max_ts = result.scalar()
    version = int(max_ts.timestamp()) if max_ts else 0
    return {"code": 200, "message": "success", "data": {"snapshot_version": version}}

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
    kb_id, needs_parse = await KnowledgeService.handle_upload(
        db, file.filename, content, parent_id, kb_tier, security_level, current_user.user_id, current_user.dept_id
    )
    await db.commit()

    if needs_parse:
        from app.tasks.worker import process_parse_task
        process_parse_task.delay(kb_id)

    return {"code": 200, "message": "success", "data": {"kb_id": kb_id, "parse_dispatched": needs_parse}}

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

    import hashlib
    content = await file.read()
    new_hash = hashlib.sha256(content).hexdigest()

    # 哈希相等性检查：内容无变化则拒绝替换
    if node.physical_file_id:
        pf_result = await db.execute(
            select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.file_id == node.physical_file_id)
        )
        pf = pf_result.scalars().first()
        if pf and pf.content_hash == new_hash:
            raise BusinessException(409, "内容无变化，无需替换")

    new_kb_id, needs_parse = await KnowledgeService.handle_upload(
        db, file.filename, content, node.parent_id, node.kb_tier, node.security_level, current_user.user_id, current_user.dept_id
    )

    node.is_deleted = True
    await db.commit()

    if needs_parse:
        from app.tasks.worker import process_parse_task
        process_parse_task.delay(new_kb_id)

    return {"code": 200, "message": "success", "data": {"kb_id": new_kb_id}}

@router.delete("/{kb_id}")
async def delete_kb_node(kb_id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await KnowledgeService.delete_node(db, kb_id, current_user.user_id)
    return {"code": 200, "message": "success", "data": None}


@router.post("/{kb_id}/reparse")
async def reparse_kb_node(kb_id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeBaseHierarchy).where(
            KnowledgeBaseHierarchy.kb_id == kb_id,
            KnowledgeBaseHierarchy.is_deleted == False
        )
    )
    node = result.scalars().first()
    if not node:
        raise BusinessException(404, "节点不存在")
    if node.parse_status != "FAILED":
        raise BusinessException(409, "仅解析失败的节点可触发重新解析")

    node.parse_status = "PARSING"
    await db.commit()

    from app.tasks.worker import process_parse_task
    process_parse_task.delay(kb_id)

    return {"code": 202, "message": "重新解析任务已派发", "data": {"kb_id": kb_id}}


from app.core.exceptions import BusinessException