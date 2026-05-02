import os
import hashlib
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.org import SystemUser
from app.models.config import DocumentType
from app.models.document import ExemplarDocument
from app.schemas.response import StandardResponse, success, error
from app.core.config import settings

router = APIRouter()

@router.post("/upload", response_model=StandardResponse)
async def upload_exemplar(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_active_user),
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type_id: int = Form(...),
    tier: str = Form("DEPT")
) -> Any:
    """上传参考范文 (P8.1, 实施约束规则 7)"""
    
    # 1. 权限校验
    if tier == "BASE" and current_user.role_level < 99:
        raise HTTPException(status_code=403, detail="Only admins can upload to BASE tier")
    
    # 2. 校验文件类型 (MIME 校验 P7.1)
    if file.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return error(code=400, message="Only .docx files are allowed (MIME check failed)")
        
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()
    
    # 3. 检查哈希去重
    stmt = select(ExemplarDocument).where(ExemplarDocument.content_hash == content_hash, ExemplarDocument.is_deleted == False)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return error(code=409, message="Exemplar with same content already exists")

    # 4. 保存文件
    file_name = f"exemplar_{content_hash[:16]}.docx"
    file_path = os.path.join(settings.STORAGE_ROOT, "exemplars", file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    # 5. 提取文本 (使用 MarkItDown 解析 docx)
    try:
        from app.services.ai_service import ai_service
        extracted_text = ai_service.parse_to_markdown(file_path)
    except Exception as e:
        # 允许降级存入，并在日志中记录 (实施约束规则 5.8)
        extracted_text = None
        # TODO: Log warning
        
    # 6. 创建记录
    exemplar = ExemplarDocument(
        title=title,
        doc_type_id=doc_type_id,
        tier=tier,
        dept_id=current_user.dept_id if tier == "DEPT" else None,
        file_path=file_path,
        content_hash=content_hash,
        extracted_text=extracted_text,
        uploader_id=current_user.user_id
    )
    db.add(exemplar)
    await db.commit()
    await db.refresh(exemplar)
    
    return success(data={"exemplar_id": exemplar.exemplar_id})

@router.get("/", response_model=StandardResponse)
async def list_exemplars(
    doc_type_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取范文列表 (按文种过滤)"""
    stmt = select(ExemplarDocument).where(ExemplarDocument.is_deleted == False)
    
    if doc_type_id:
        stmt = stmt.where(ExemplarDocument.doc_type_id == doc_type_id)
        
    # 层级过滤: BASE 全员可见, DEPT 仅本科室可见
    stmt = stmt.where(
        (ExemplarDocument.tier == "BASE") | 
        (ExemplarDocument.dept_id == current_user.dept_id)
    )
    
    result = await db.execute(stmt)
    return success(data=result.scalars().all())

@router.get("/{exemplar_id}/preview", response_model=StandardResponse)
async def preview_exemplar(
    exemplar_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """范文纯文本预览 (P8.2)"""
    exemplar = await db.get(ExemplarDocument, exemplar_id)
    if not exemplar or exemplar.is_deleted:
        return error(code=404, message="Exemplar not found")
        
    return success(data={"text": exemplar.extracted_text or "No text extracted yet"})

@router.delete("/{exemplar_id}", response_model=StandardResponse)
async def delete_exemplar(
    exemplar_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """软删除范文 (P8.3)"""
    exemplar = await db.get(ExemplarDocument, exemplar_id)
    if not exemplar:
        return error(code=404, message="Exemplar not found")
        
    # 范文引用保护 (实施约束规则 11): 检查是否有 DRAFTING 公文在用它
    from app.models.document import Document, DocStatus
    from sqlalchemy import func
    stmt = select(func.count(Document.doc_id)).where(
        Document.exemplar_id == exemplar_id,
        Document.status == DocStatus.DRAFTING,
        Document.is_deleted == False
    )
    count = (await db.execute(stmt)).scalar()
    if count > 0:
        return error(code=409, message=f"Cannot delete exemplar: referenced by {count} drafting document(s)")
        
    # 检查是否有正在处理或排队的POLISH任务依赖此范文
    from app.models.task import AsyncTask, TaskType, TaskStatus
    stmt_task = select(func.count(AsyncTask.task_id)).join(
        Document, AsyncTask.doc_id == Document.doc_id
    ).where(
        AsyncTask.task_type == TaskType.POLISH,
        AsyncTask.task_status.in_([TaskStatus.QUEUED, TaskStatus.PROCESSING]),
        Document.exemplar_id == exemplar_id
    )
    task_count = (await db.execute(stmt_task)).scalar()
    if task_count > 0:
        return error(code=409, message=f"Cannot delete exemplar: referenced by {task_count} active polish task(s)")

    exemplar.is_deleted = True
    await db.commit()
    return success(message="Exemplar soft-deleted")
