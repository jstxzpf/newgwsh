from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgePhysicalFile
from app.models.enums import KBTier, DataSecurityLevel
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import hashlib
import os

router = APIRouter()

@router.get("/hierarchy")
async def get_hierarchy(tier: KBTier = KBTier.PERSONAL, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False)
    if tier == KBTier.PERSONAL:
        query = query.where(KnowledgeBaseHierarchy.owner_id == current_user.user_id)
    elif tier == KBTier.DEPT:
        query = query.where(KnowledgeBaseHierarchy.dept_id == current_user.dept_id)
    
    result = await db.execute(query)
    items = result.scalars().all()
    # 在实际中这里应该构造嵌套树，暂返回扁平列表供演示
    return {"code": 200, "message": "success", "data": [item.kb_name for item in items]}

@router.get("/snapshot-version")
async def get_snapshot_version(current_user: SystemUser = Depends(get_current_user)):
    import time
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
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 检查物理去重
    result = await db.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == file_hash))
    phys_file = result.scalars().first()
    
    if not phys_file:
        # 这里应该写文件到磁盘，为了简化暂只记录数据库
        phys_file = KnowledgePhysicalFile(content_hash=file_hash, file_path=f"/fake/path/{file.filename}", file_size=len(content))
        db.add(phys_file)
        await db.flush()
        
    kb_node = KnowledgeBaseHierarchy(
        parent_id=parent_id,
        kb_name=file.filename,
        kb_type="FILE",
        kb_tier=kb_tier,
        dept_id=current_user.dept_id,
        security_level=security_level,
        parse_status="UPLOADED" if not phys_file.file_size else "READY", # 简化
        physical_file_id=phys_file.file_id,
        owner_id=current_user.user_id
    )
    db.add(kb_node)
    await db.commit()
    
    return {"code": 200, "message": "success", "data": {"kb_id": kb_node.kb_id}}