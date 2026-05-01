import time
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.api import deps
from app.models.org import SystemUser
from app.models.knowledge import KnowledgeBaseHierarchy, KbType, KbTier, SecurityLevel
from app.services.knowledge_file import KnowledgeFileService
from app.services.knowledge_hierarchy import KnowledgeHierarchyService
from app.schemas.response import StandardResponse, success, error

from app.tasks.worker import parse_knowledge

router = APIRouter()

@router.post("/upload", response_model=StandardResponse)
async def upload_file(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user),
    file: UploadFile = File(...),
    kb_tier: KbTier = Form(KbTier.PERSONAL),
    parent_id: Optional[int] = Form(None),
    security_level: SecurityLevel = Form(SecurityLevel.GENERAL)
) -> Any:
    """上传知识库文件/压缩包并触发解析流 (P8.3)"""
    
    filename = file.filename
    content = await file.read()
    
    # 如果是压缩包, 派发后台任务递归处理
    if filename.endswith(('.zip', '.tar.gz')):
        from app.tasks.worker import process_zip_upload
        # 先存物理文件
        physical_file_id, _ = await KnowledgeFileService.save_physical_file(
            db, content, filename, security_level
        )
        # 记录审计
        db.add(WorkflowAudit(
            workflow_node_id=50, operator_id=current_user.user_id,
            action_details={"kb_name": filename, "type": "ZIP"}
        ))
        await db.commit()
        
        process_zip_upload.delay(
            physical_file_id=physical_file_id,
            kb_tier=kb_tier.value,
            parent_id=parent_id,
            security_level=security_level,
            owner_id=current_user.user_id,
            dept_id=current_user.dept_id
        )
        return success(message="Zip upload task triggered")

    # 1. 保存普通物理文件 (包含哈希去重与安全等级复用校验 P5.1 契约)
    physical_file_id, existing_kb_id_for_reuse = await KnowledgeFileService.save_physical_file(
        db, content, filename, security_level
    )
    
    # 2. 创建层级逻辑节点
    node = await KnowledgeHierarchyService.create_node(
        db,
        kb_name=file.filename,
        kb_type=KbType.FILE,
        kb_tier=kb_tier,
        security_level=security_level,
        parent_id=parent_id,
        physical_file_id=physical_file_id,
        owner_id=current_user.user_id,
        dept_id=current_user.dept_id
    )
    
    # 3. 触发解析或复用切片
    from app.models.audit import WorkflowAudit
    audit = WorkflowAudit(
        doc_id=None,
        workflow_node_id=50, # KB_UPLOADED
        operator_id=current_user.user_id,
        action_details={"kb_id": node.kb_id, "kb_name": node.kb_name, "tier": kb_tier.value}
    )
    db.add(audit)
    await db.commit()

    if existing_kb_id_for_reuse:
        # 命中切片复用契约 (等级一致场景)
        await KnowledgeHierarchyService.reuse_chunks(db, existing_kb_id_for_reuse, node)
        return success(data={"kb_id": node.kb_id, "parse_triggered": False, "status": "READY"})
    else:
        # 新文件或等级不一致场景，强制重新解析
        parse_knowledge.delay(node.kb_id)
        return success(data={"kb_id": node.kb_id, "parse_triggered": True, "status": "PARSING"})

@router.get("/hierarchy", response_model=StandardResponse)
async def list_kb_assets(
    kb_tier: Optional[KbTier] = None,
    parent_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取知识库目录树 (带权限隔离 P8)"""
    stmt = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False)
    
    if kb_tier:
        stmt = stmt.where(KnowledgeBaseHierarchy.kb_tier == kb_tier)
    if parent_id:
        stmt = stmt.where(KnowledgeBaseHierarchy.parent_id == parent_id)
        
    # 权限过滤
    if current_user.role_level < 99:
        from sqlalchemy import or_
        filters = []
        filters.append(KnowledgeBaseHierarchy.kb_tier == KbTier.BASE)
        filters.append((KnowledgeBaseHierarchy.kb_tier == KbTier.DEPT) & (KnowledgeBaseHierarchy.dept_id == current_user.dept_id))
        filters.append((KnowledgeBaseHierarchy.kb_tier == KbTier.PERSONAL) & (KnowledgeBaseHierarchy.owner_id == current_user.user_id))
        stmt = stmt.where(or_(*filters))
        
    result = await db.execute(stmt)
    return success(data=result.scalars().all())

@router.get("/snapshot-version", response_model=StandardResponse)
async def get_kb_snapshot_version(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取目录树版本号 (最新更新时间戳 P8)"""
    from sqlalchemy import func
    stmt = select(func.max(KnowledgeBaseHierarchy.updated_at))
    result = await db.execute(stmt)
    max_updated = result.scalar()
    version = int(max_updated.timestamp()) if max_updated else int(time.time())
    return success(data={"snapshot_version": version})

@router.delete("/{kb_id}", response_model=StandardResponse)
async def delete_kb_node(
    kb_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """递归软删除知识库目录或文件 (P5.1)"""
    # 1. 检查是否存在
    node = await db.get(KnowledgeBaseHierarchy, kb_id)
    if not node or node.is_deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    # 2. 权限校验
    if node.owner_id != current_user.user_id and current_user.role_level < 5:
        raise HTTPException(status_code=403, detail="No permission to delete")
        
    # 3. 记录审计
    from app.models.audit import WorkflowAudit
    audit = WorkflowAudit(
        doc_id=None,
        workflow_node_id=51, # KB_DELETED
        operator_id=current_user.user_id,
        action_details={"kb_id": kb_id, "kb_name": node.kb_name}
    )
    db.add(audit)

    # 4. 递归删除
    await KnowledgeHierarchyService.soft_delete_subtree(db, kb_id)
    
    return success(message="Asset and its sub-items soft-deleted")
