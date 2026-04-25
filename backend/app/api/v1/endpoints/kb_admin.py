from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.kb_service import KBService
from app.core.enums import KBTier, DataSecurityLevel, TaskType, TaskStatus
from app.models.document import AsyncTask
from app.tasks.worker import parse_kb_file_task
import uuid
import json
from app.core.redis import redis_client

router = APIRouter()

@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    kb_tier: KBTier = Form(KBTier.PERSONAL),
    security_level: DataSecurityLevel = Form(DataSecurityLevel.GENERAL),
    user_id: int = 1, # 临时 Mock
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # 1. 处理物理文件
        phys_file = await KBService.get_or_create_physical_file(db, file)
        
        # 2. 创建逻辑节点
        node = await KBService.create_hierarchy_node(
            db, file.filename, phys_file.file_id, user_id, kb_tier, security_level
        )
        
        # 3. 触发解析任务
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
        
        # 派发 Celery
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
async def get_hierarchy(db: AsyncSession = Depends(get_async_db)):
    from sqlalchemy import select
    from app.models.knowledge import KnowledgeBaseHierarchy
    
    result = await db.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False))
    nodes = result.scalars().all()
    return {"data": nodes}
