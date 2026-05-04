from fastapi import APIRouter, Depends, UploadFile, File, Form
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
async def get_hierarchy(tier: KBTier = KBTier.PERSONAL, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False)
    if tier == KBTier.PERSONAL:
        query = query.where(KnowledgeBaseHierarchy.owner_id == current_user.user_id)
    elif tier == KBTier.DEPT:
        query = query.where(KnowledgeBaseHierarchy.dept_id == current_user.dept_id)
    
    result = await db.execute(query)
    items = result.scalars().all()
    return {"code": 200, "message": "success", "data": [item.kb_name for item in items]}

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
    content = await file.read()
    kb_id = await KnowledgeService.handle_upload(
        db, file.filename, content, parent_id, kb_tier, security_level, current_user.user_id, current_user.dept_id
    )
    await db.commit()
    return {"code": 200, "message": "success", "data": {"kb_id": kb_id}}