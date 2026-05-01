import hashlib
import io
import os
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.document import Document, DocStatus, DocumentSnapshot
from app.models.org import SystemUser
from app.models.audit import WorkflowAudit, DocumentApprovalLog
from app.schemas.document import DocumentCreate, DocumentRead, DocumentAutoSave, DocumentDetail
from app.schemas.response import StandardResponse, success, error
from app.core.locks import lock_manager
from app.core.sip import generate_sip_hash

router = APIRouter()

@router.post("/init", response_model=StandardResponse[DocumentRead])
async def init_document(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user),
    doc_in: DocumentCreate
) -> Any:
    """新建公文: 状态置为 DRAFTING(10)"""
    new_doc = Document(
        title=doc_in.title,
        doc_type_id=doc_in.doc_type_id,
        creator_id=current_user.user_id,
        dept_id=current_user.dept_id,
        status=DocStatus.DRAFTING
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    
    # 记录审计 (WorkflowNode: 10=DRAFTING)
    audit = WorkflowAudit(
        doc_id=new_doc.doc_id,
        workflow_node_id=10,
        operator_id=current_user.user_id
    )
    db.add(audit)
    await db.commit()
    
    return success(data=new_doc)

@router.get("/", response_model=StandardResponse)
async def list_documents(
    status: Optional[DocStatus] = None,
    dept_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user),
) -> Any:
    """公文大厅列表 (带权限隔离 P5.1)"""
    stmt = select(Document).where(Document.is_deleted == False)
    
    # 权限隔离逻辑 (对照《API契约》)
    if current_user.role_level < 99:
        if current_user.role_level >= 5:
            # 科长可见本科室
            stmt = stmt.where(Document.dept_id == current_user.dept_id)
        else:
            # 科员排除他人 DRAFTING 状态草稿
            stmt = stmt.where(
                (Document.creator_id == current_user.user_id) | 
                (Document.status != DocStatus.DRAFTING)
            )
    
    if status:
        stmt = stmt.where(Document.status == status)
    if dept_id:
        stmt = stmt.where(Document.dept_id == dept_id)
        
    stmt = stmt.order_by(Document.updated_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return success(data={"items": items, "total": len(items)})

@router.get("/{doc_id}", response_model=StandardResponse[DocumentDetail])
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user),
) -> Any:
    """获取公文详情"""
    stmt = select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error(code=404, message="Document not found")
    
    return success(data=doc)

@router.post("/{doc_id}/auto-save", response_model=StandardResponse)
async def auto_save(
    doc_id: str,
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user),
    save_in: DocumentAutoSave
) -> Any:
    """
    自动保存接口 (P0 级防死锁与 DIFF 保护逻辑)
    """
    stmt = select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error(code=404, message="Document not found")

    # 1. 锁归属校验 (P7.2 铁律)
    if save_in.lock_token:
        # 如果前端传了 token，验证其有效性
        is_locked = await lock_manager.verify_lock(doc_id, save_in.lock_token)
        if not is_locked:
            return error(code=423, message="Lock expired or invalid")
    elif doc.creator_id != current_user.user_id and current_user.role_level < 99:
        return error(code=403, message="No permission to edit this document")

    # 2. DIFF 模式保护矩阵 (对照《后端设计方案.md》)
    is_diff_mode = doc.ai_polished_content is not None
    
    if is_diff_mode:
        if save_in.content is not None:
            return error(code=400, message="Cannot update original content in DIFF mode")
        if save_in.draft_content:
            doc.draft_suggestion = save_in.draft_content
    else:
        if save_in.content is not None:
            new_content_hash = hashlib.sha256(save_in.content.encode()).hexdigest()
            old_content_hash = hashlib.sha256((doc.content or "").encode()).hexdigest()
            if new_content_hash != old_content_hash:
                doc.content = save_in.content
    
    if save_in.title:
        doc.title = save_in.title
        
    await db.commit()
    return success(message="Auto-saved successfully")

@router.post("/{doc_id}/snapshots", response_model=StandardResponse)
async def create_snapshot(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """手动创建公文快照"""
    doc = await db.get(Document, doc_id)
    if not doc:
        return error(code=404, message="Document not found")
        
    snapshot = DocumentSnapshot(
        doc_id=doc.doc_id,
        content=doc.content,
        trigger_event="manual_snapshot",
        creator_id=current_user.user_id
    )
    db.add(snapshot)
    db.add(WorkflowAudit(doc_id=doc.doc_id, workflow_node_id=11, operator_id=current_user.user_id, action_details={"reason": "manual"}))
    await db.commit()
    return success(message="Snapshot created successfully")

@router.post("/{doc_id}/submit", response_model=StandardResponse)
async def submit_document(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """提交审批: 校验锁并进入 SUBMITTED(30) 状态"""
    stmt = select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 1. 锁校验 (后端设计方案 3.3 提交验证与释放)
    lock_key = f"lock:{doc_id}"
    lock_data_raw = await lock_manager.redis.get(lock_key)
    if lock_data_raw:
        import json
        lock_data = json.loads(lock_data_raw)
        if lock_data.get("user_id") != current_user.user_id:
            return error(code=423, message=f"Document is currently locked by {lock_data.get('username')}")
        # 匹配则允许提交并主动删除锁
        await lock_manager.redis.delete(lock_key)
    else:
        # 如果锁已过期，校验是否为创建者或管理员 (P3.3 权限底线拦截)
        if doc.creator_id != current_user.user_id and current_user.role_level < 99:
            return error(code=403, message="Lock expired and you are not the creator, submission denied")
    
    # 2. 状态变更
    try:
        doc.status = DocStatus.SUBMITTED
    except ValueError as e:
        return error(code=409, message=str(e))
    
    import asyncio
    from app.core.database import AsyncSessionLocal
    
    # 异步写入审计日志 (实施约束规则 5)
    async def write_audit_log_async(doc_id: str, node_id: int, operator_id: int):
        async with AsyncSessionLocal() as audit_db:
            audit = WorkflowAudit(
                doc_id=doc_id,
                workflow_node_id=node_id,
                operator_id=operator_id
            )
            audit_db.add(audit)
            await audit_db.commit()

    asyncio.create_task(write_audit_log_async(doc.doc_id, 30, current_user.user_id))
    
    # 4. 记录到审批日志表 (待审状态, 包含 submitted_at)
    from datetime import datetime, timezone
    log_entry = DocumentApprovalLog(
        doc_id=doc.doc_id,
        submitter_id=current_user.user_id,
        decision_status="SUBMITTED",
        submitted_at=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    
    await db.commit()
    return success(message="Document submitted for approval")

@router.post("/{doc_id}/revise", response_model=StandardResponse)
async def revise_document(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """驳回后重修: 原子性抢锁并回退至 DRAFTING(10)"""
    stmt = select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc or doc.status != DocStatus.REJECTED:
        return error(code=409, message="Only rejected documents can be revised")

    # 1. 原子性抢锁 (P7.1 铁律)
    lock_res = await lock_manager.acquire_lock(doc_id, current_user.user_id, current_user.full_name)
    if not lock_res:
        return error(code=423, message="Failed to acquire lock for revision")
    
    # 2. 回退状态
    doc.status = DocStatus.DRAFTING
    doc.ai_polished_content = None 
    doc.draft_suggestion = None
    
    # 3. 记录审计
    audit = WorkflowAudit(
        doc_id=doc.doc_id,
        workflow_node_id=42,
        operator_id=current_user.user_id
    )
    db.add(audit)
    await db.commit()
    
    return success(data=lock_res, message="Document returned to drafting mode with lock")

@router.post("/{doc_id}/apply-polish", response_model=StandardResponse)
async def apply_polish(
    doc_id: str,
    final_content: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """接受 AI 润色: 备份原稿并覆写 (P5.1 原子性铁律)"""
    async with db.begin():
        stmt = select(Document).where(Document.doc_id == doc_id).with_for_update()
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc or doc.status != DocStatus.DRAFTING:
            return error(code=409, message="Invalid state for applying polish")
            
        # 1. 创建备份快照 (WorkflowNode: 11=SNAPSHOT)
        snapshot = DocumentSnapshot(
            doc_id=doc.doc_id,
            content=doc.content,
            trigger_event="apply_polish",
            creator_id=current_user.user_id
        )
        db.add(snapshot)
        db.add(WorkflowAudit(doc_id=doc.doc_id, workflow_node_id=11, operator_id=current_user.user_id))
        
        # 2. 覆写正文并清理润色字段
        doc.content = final_content
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        
        # 3. 记录审计 (WorkflowNode: 21=POLISH_APPLIED)
        db.add(WorkflowAudit(doc_id=doc.doc_id, workflow_node_id=21, operator_id=current_user.user_id))
        
    return success(message="Polish applied and original content backed up")

@router.post("/{doc_id}/discard-polish", response_model=StandardResponse)
async def discard_polish(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """丢弃 AI 润色"""
    stmt = select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        return error(code=404, message="Document not found")
        
    doc.ai_polished_content = None
    doc.draft_suggestion = None
    await db.commit()
    return success(message="Polish discarded")

@router.get("/{doc_id}/snapshots", response_model=StandardResponse)
async def list_snapshots(
    doc_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """获取快照列表"""
    stmt = select(DocumentSnapshot).where(DocumentSnapshot.doc_id == doc_id)
    stmt = stmt.order_by(DocumentSnapshot.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return success(data=result.scalars().all())

@router.post("/{doc_id}/snapshots/{snapshot_id}/restore", response_model=StandardResponse)
async def restore_snapshot(
    doc_id: str,
    snapshot_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """恢复快照"""
    async with db.begin():
        snapshot = await db.get(DocumentSnapshot, snapshot_id)
        if not snapshot or snapshot.doc_id != doc_id:
            return error(code=404, message="Snapshot not found")
        doc = await db.get(Document, doc_id)
        if not doc or doc.status != DocStatus.DRAFTING:
            return error(code=409, message="Illegal state")
        doc.content = snapshot.content
        db.add(WorkflowAudit(doc_id=doc.doc_id, workflow_node_id=12, operator_id=current_user.user_id))
    return success(message="Snapshot restored")

@router.get("/{doc_id}/verify-sip", response_model=StandardResponse)
async def verify_sip(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """校验 SIP 存证"""
    stmt = select(DocumentApprovalLog).where(
        DocumentApprovalLog.doc_id == doc_id,
        DocumentApprovalLog.decision_status == "APPROVED"
    ).order_by(DocumentApprovalLog.reviewed_at.desc())
    log = (await db.execute(stmt)).scalar_one_or_none()
    
    if not log or not log.sip_hash:
        return error(code=404, message="SIP record not found")
        
    doc = await db.get(Document, doc_id)
    current_sip = generate_sip_hash(doc.content or "", log.reviewer_id, log.reviewed_at.isoformat())
    return success(data={"is_valid": current_sip == log.sip_hash})

@router.get("/{doc_id}/download")
async def download_docx(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """下载 Word (P2.12)"""
    doc = await db.get(Document, doc_id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not doc.word_output_path or not os.path.exists(doc.word_output_path):
        raise HTTPException(status_code=404, detail="Word file not ready or not found")
        
    from fastapi.responses import FileResponse
    # 获取文件名
    filename = os.path.basename(doc.word_output_path)
    return FileResponse(
        path=doc.word_output_path, 
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@router.delete("/{doc_id}", response_model=StandardResponse)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """软删除"""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc.is_deleted = True
    await db.commit()
    return success(message="Deleted")
