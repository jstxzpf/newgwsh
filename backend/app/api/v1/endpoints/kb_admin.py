from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.kb_service import KBService
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.enums import KBTier, DataSecurityLevel, TaskType, TaskStatus
from app.models.document import AsyncTask
from app.tasks.worker import parse_kb_file_task
from sqlalchemy import select, or_
from app.models.knowledge import KnowledgeBaseHierarchy
from pydantic import BaseModel
from typing import Optional, List
import uuid
import json
from app.core.redis import get_redis

router = APIRouter()

class KBNodeOut(BaseModel):
    kb_id: int
    kb_name: str
    kb_type: str
    kb_tier: str
    security_level: str
    dept_id: Optional[int]
    parent_id: Optional[int]
    owner_id: int
    parse_status: str
    file_version: int
    children: List["KBNodeOut"] = []
    model_config = {"from_attributes": True}

KBNodeOut.model_rebuild()

@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    kb_tier: KBTier = Form(KBTier.PERSONAL),
    security_level: DataSecurityLevel = Form(DataSecurityLevel.GENERAL),
    parent_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 1. 颗粒度对齐：校验上传权限层级
    if kb_tier == KBTier.BASE and current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Only admin can upload to BASE tier")
    if kb_tier == KBTier.DEPT and current_user.role_level < 5:
        raise HTTPException(status_code=403, detail="Only department head can upload to DEPT tier")

    # 2. 【高危修复】校验父目录授权
    if parent_id is not None:
        parent_res = await db.execute(
            select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == parent_id)
        )
        parent = parent_res.scalars().first()
        if not parent:
            raise HTTPException(status_code=404, detail="父目录不存在")
        if parent.kb_type != "DIRECTORY":
            raise HTTPException(status_code=400, detail="父节点必须是目录")
        if parent.kb_tier == KBTier.PERSONAL and parent.owner_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="无权挂载到他人的个人目录")
        if parent.kb_tier == KBTier.DEPT and (current_user.dept_id != parent.dept_id or current_user.role_level < 5):
            raise HTTPException(status_code=403, detail="无权挂载到非本科室的科室目录")

    try:
        phys_file = await KBService.get_or_create_physical_file(db, file)
        node = await KBService.create_hierarchy_node(
            db, file.filename, phys_file.file_id, current_user.user_id, current_user.dept_id, kb_tier, security_level, parent_id
        )
        task_id = str(uuid.uuid4())
        new_task = AsyncTask(
            task_id=task_id,
            task_type=TaskType.PARSE,
            kb_id=node.kb_id,
            creator_id=current_user.user_id,
            task_status=TaskStatus.QUEUED,
            input_params={"file_path": phys_file.file_path, "filename": file.filename}
        )
        db.add(new_task)
        node.parse_status = "PARSING"
        await db.commit()
        
        parse_kb_file_task.apply_async(args=[node.kb_id, phys_file.file_path], task_id=task_id)
        
        redis_client = await get_redis()
        await redis_client.set(f"task_status:{task_id}", json.dumps({
            "progress": 0,
            "status": TaskStatus.QUEUED.value,
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

@router.put("/{kb_id}/replace")
async def replace_knowledge_version(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 【高危修复】校验归属权
    node_res = await db.execute(
        select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == kb_id)
    )
    node = node_res.scalars().first()
    if not node:
        raise HTTPException(status_code=404, detail="资产不存在")
    if node.owner_id != current_user.user_id and current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="无权替换他人资产")

    try:
        phys_file = await KBService.get_or_create_physical_file(db, file)
        await KBService.replace_kb_node(db, kb_id, file.filename, phys_file.file_id, current_user.user_id)
            
        task_id = str(uuid.uuid4())
        new_task = AsyncTask(
            task_id=task_id,
            task_type=TaskType.PARSE,
            kb_id=kb_id,
            creator_id=current_user.user_id,
            task_status=TaskStatus.QUEUED,
            input_params={"file_path": phys_file.file_path, "filename": file.filename}
        )
        db.add(new_task)
        await db.commit()
        
        parse_kb_file_task.apply_async(args=[kb_id, phys_file.file_path], task_id=task_id)
        return {"status": "success", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hierarchy", response_model=List[KBNodeOut])
async def get_hierarchy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 构建基础查询（排除已软删）
    stmt = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False)
    
    # 【水平越权修复】按照 KBTier 构建科室屏障
    condition = or_(
        KnowledgeBaseHierarchy.kb_tier == KBTier.BASE,
        (KnowledgeBaseHierarchy.kb_tier == KBTier.DEPT) & (KnowledgeBaseHierarchy.dept_id == current_user.dept_id), 
        (KnowledgeBaseHierarchy.kb_tier == KBTier.PERSONAL) & (KnowledgeBaseHierarchy.owner_id == current_user.user_id)
    )
    
    result = await db.execute(stmt.where(condition))
    nodes = result.scalars().all()

    # 【对齐修复】构建递归树形结构
    node_map = {}
    for n in nodes:
        m = KBNodeOut.model_validate(n)
        m.children = [] # 显式初始化防脏
        node_map[m.kb_id] = m
        
    roots = []
    for n in nodes:
        m = node_map[n.kb_id]
        if n.parent_id and n.parent_id in node_map:
            node_map[n.parent_id].children.append(m)
        else:
            roots.append(m)
            
    return roots

@router.post("/batch-upload")
async def batch_upload_knowledge_files(
    files: List[UploadFile] = File(...),
    kb_tier: KBTier = Form(KBTier.PERSONAL),
    security_level: DataSecurityLevel = Form(DataSecurityLevel.GENERAL),
    parent_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 【对齐修复】前置校验父目录授权 (仅需校验一次)
    if parent_id is not None:
        parent_res = await db.execute(
            select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == parent_id)
        )
        parent = parent_res.scalars().first()
        if not parent:
            raise HTTPException(status_code=404, detail="父目录不存在")
        if parent.kb_type != "DIRECTORY":
            raise HTTPException(status_code=400, detail="父节点必须是目录")
        if parent.kb_tier == KBTier.PERSONAL and parent.owner_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="无权挂载到他人的个人目录")
        if parent.kb_tier == KBTier.DEPT and (current_user.dept_id != parent.dept_id or current_user.role_level < 5):
            raise HTTPException(status_code=403, detail="无权挂载到非本科室的科室目录")

    results = []
    for file in files:
        try:
            phys_file = await KBService.get_or_create_physical_file(db, file)
            node = await KBService.create_hierarchy_node(
                db, file.filename, phys_file.file_id, current_user.user_id, current_user.dept_id, kb_tier, security_level, parent_id
            )
            task_id = str(uuid.uuid4())
            new_task = AsyncTask(
                task_id=task_id,
                task_type=TaskType.PARSE,
                kb_id=node.kb_id,
                creator_id=current_user.user_id,
                task_status=TaskStatus.QUEUED,
                input_params={"file_path": phys_file.file_path, "filename": file.filename}
            )
            db.add(new_task)
            node.parse_status = "PARSING"
            await db.commit()
            parse_kb_file_task.apply_async(args=[node.kb_id, phys_file.file_path], task_id=task_id)
            results.append({"filename": file.filename, "status": "success", "task_id": task_id})
        except Exception as e:
            results.append({"filename": file.filename, "status": "failed", "error": str(e)})
            
    return {"results": results}

@router.delete("/{kb_id}")
async def delete_knowledge_node(
    kb_id: int,
    background_tasks: BackgroundTasks, # 新增
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 权限校验：仅本人或管理员可删
    stmt = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == kb_id)
    res = await db.execute(stmt)
    node = res.scalars().first()
    if not node:
        raise HTTPException(status_code=404)
        
    if node.owner_id != current_user.user_id and current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        await KBService.delete_kb_node(db, kb_id)
        
        # 【对齐修复】添加审计日志
        background_tasks.add_task(
            AuditService.write_audit_log,
            str(kb_id), # 此处 doc_id 字段借用于资产 ID
            WorkflowNode.REVISION, # 借用
            current_user.user_id,
            {"note": f"知识库节点被软删除: {node.kb_name}"}
        )
        
        return {"status": "success", "message": "Node and its children marked as deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
