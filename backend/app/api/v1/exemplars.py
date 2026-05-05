from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import ExemplarDocument, Document
from app.api.dependencies import get_current_user
from app.core.exceptions import BusinessException
import hashlib
import os

router = APIRouter()

@router.get("")
async def list_exemplars(
    doc_type_id: int | None = None,
    tier: str | None = None,
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(ExemplarDocument).where(ExemplarDocument.is_deleted == False)
    
    # 权限隔离：BASE 全员，DEPT 仅本科室 (§10)
    from sqlalchemy import or_
    query = query.where(or_(
        ExemplarDocument.tier == "BASE",
        (ExemplarDocument.tier == "DEPT") & (ExemplarDocument.dept_id == current_user.dept_id)
    ))

    if doc_type_id:
        query = query.where(ExemplarDocument.doc_type_id == doc_type_id)
    if tier:
        query = query.where(ExemplarDocument.tier == tier)

    result = await db.execute(query)
    items = result.scalars().all()
    
    return {"code": 200, "message": "success", "data": [
        {
            "exemplar_id": i.exemplar_id,
            "title": i.title,
            "doc_type_id": i.doc_type_id,
            "tier": i.tier,
            "created_at": i.created_at
        } for i in items
    ]}

@router.post("/upload")
async def upload_exemplar(
    title: str = Form(...),
    doc_type_id: int = Form(...),
    tier: str = Form("DEPT"),
    file: UploadFile = File(...),
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 权限校验：管理员或科室负责人 (§10)
    if current_user.role_level < 5:
        raise BusinessException(403, "无权上传范文")
    if tier == "BASE" and current_user.role_level < 99:
        raise BusinessException(403, "仅管理员可上传全局范文")

    # MIME 校验 (§7)
    if file.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        raise BusinessException(400, "仅接受 .docx 格式范文")

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()
    
    # 去重
    result = await db.execute(select(ExemplarDocument).where(ExemplarDocument.content_hash == content_hash, ExemplarDocument.is_deleted == False))
    if result.scalars().first():
        raise BusinessException(409, "相同内容的范文已存在")

    file_path = f"/app/data/exemplars/{content_hash}.docx"
    # 模拟保存
    
    new_ex = ExemplarDocument(
        title=title,
        doc_type_id=doc_type_id,
        tier=tier,
        dept_id=current_user.dept_id if tier == "DEPT" else None,
        file_path=file_path,
        content_hash=content_hash,
        uploader_id=current_user.user_id,
        extracted_text="（模拟提取内容）" # 实际应由 worker 提取
    )
    db.add(new_ex)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"exemplar_id": new_ex.exemplar_id}}

@router.get("/{id}/preview")
async def preview_exemplar(id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExemplarDocument).where(ExemplarDocument.exemplar_id == id))
    ex = result.scalars().first()
    if not ex or ex.is_deleted:
        raise BusinessException(404, "范文不存在")
    return {"code": 200, "message": "success", "data": {"content": ex.extracted_text}}

@router.delete("/{id}")
async def delete_exemplar(id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 权限校验
    if current_user.role_level < 5:
        raise BusinessException(403, "无权删除范文")

    result = await db.execute(select(ExemplarDocument).where(ExemplarDocument.exemplar_id == id))
    ex = result.scalars().first()
    if not ex:
        raise BusinessException(404, "范文不存在")

    # 引用保护 (§11)
    ref_result = await db.execute(select(Document).where(Document.exemplar_id == id, Document.status == "DRAFTING"))
    if ref_result.scalars().first():
        raise BusinessException(409, "该范文正被草稿引用，无法删除")

    ex.is_deleted = True
    await db.commit()
    return {"code": 200, "message": "success", "data": None}