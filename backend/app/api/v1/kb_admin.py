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
    
    # 按照契约返回嵌套树结构（简化示例：目前仅返回扁平列表，实际应递归）
    return {
        "code": 200, 
        "message": "success", 
        "data": [
            {
                "kb_id": item.kb_id, 
                "kb_name": item.kb_name, 
                "kb_type": item.kb_type, 
                "security_level": item.security_level,
                "parse_status": item.parse_status
            } for item in items
        ]
    }

@router.get("/snapshot-version")
async def get_snapshot_version(current_user: SystemUser = Depends(get_current_user)):
    # 契约要求返回时间戳 §8
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
    # 权限校验：DEPT/BASE 需要更高权限 §二.2
    if kb_tier == KBTier.BASE and current_user.role_level < 99:
        raise BusinessException(403, "无权写入基础库")
    if kb_tier == KBTier.DEPT and current_user.role_level < 5:
        raise BusinessException(403, "无权写入科室库")

    content = await file.read()
    kb_id = await KnowledgeService.handle_upload(
        db, file.filename, content, parent_id, kb_tier, security_level, current_user.user_id, current_user.dept_id
    )
    await db.commit()
    
    # 派发解析任务
    from app.tasks.worker import process_parse_task
    process_parse_task.delay(kb_id)
    
    return {"code": 200, "message": "success", "data": {"kb_id": kb_id}}

@router.delete("/{kb_id}")
async def delete_kb_node(kb_id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 铁律：级联软删除 §三.2
    await KnowledgeService.delete_node(db, kb_id)
    return {"code": 200, "message": "success", "data": None}

from app.core.exceptions import BusinessException