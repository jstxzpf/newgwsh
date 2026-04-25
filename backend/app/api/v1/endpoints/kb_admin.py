from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.kb_service import KBService
from app.core.enums import KBTier, DataSecurityLevel, TaskType, TaskStatus
from app.models.document import AsyncTask
from app.tasks.worker import parse_kb_file_task
from sqlalchemy import select, or_
from app.models.knowledge import KnowledgeBaseHierarchy
import uuid
import json
from app.core.redis import redis_client

router = APIRouter()

@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    kb_tier: KBTier = Form(KBTier.PERSONAL),
    security_level: DataSecurityLevel = Form(DataSecurityLevel.GENERAL),
    user_id: int = 1, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        phys_file = await KBService.get_or_create_physical_file(db, file)
        node = await KBService.create_hierarchy_node(
            db, file.filename, phys_file.file_id, user_id, kb_tier, security_level
        )
        task_id = str(uuid.uuid4())
        new_task = AsyncTask(
            task_id=task_id,
            task_type=TaskType.PARSE,
            kb_id=node.kb_id,
            creator_id=user_id,
            task_status=TaskStatus.QUEUED,
            input_params={"file_path": phys_file.file_path, "filename": file.filename}
        )
        db.add(new_task)
        node.parse_status = "PARSING"
        await db.commit()
        
        parse_kb_file_task.apply_async(args=[node.kb_id, phys_file.file_path], task_id=task_id)
        
        await redis_client.set(f"task_status:{task_id}", json.dumps({
            "progress": 0,
            "status": TaskStatus.QUEUED,
            "result": None
        }), ex=3600)
        
        return {
            "status": "success", 
            "kb_id": node.kb_id, 
            "task_id": task_id, 
            "message": "File uploaded and parsing started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hierarchy")
async def get_hierarchy(
    user_id: int = 1, # TODO: Mock
    dept_id: int = 1, # TODO: Mock
    db: AsyncSession = Depends(get_async_db)
):
    # 构建基础查询（排除已软删）
    stmt = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False)
    
    # 按照 KBTier 构建权限屏障条件 (二次除错补强：防止个人库越权泄露)
    condition = or_(
        KnowledgeBaseHierarchy.kb_tier == KBTier.BASE,
        # 暂时简化：DEPT 暂不强制校验 dept_id（待后续扩展）
        (KnowledgeBaseHierarchy.kb_tier == KBTier.DEPT), 
        (KnowledgeBaseHierarchy.kb_tier == KBTier.PERSONAL) & (KnowledgeBaseHierarchy.owner_id == user_id)
    )
    
    result = await db.execute(stmt.where(condition))
    nodes = result.scalars().all()
    return {"data": nodes}

@router.delete("/{kb_id}")
async def delete_knowledge_node(
    kb_id: int,
    user_id: int = 1, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        await KBService.delete_kb_node(db, kb_id)
        return {"status": "success", "message": "Node and its children marked as deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
