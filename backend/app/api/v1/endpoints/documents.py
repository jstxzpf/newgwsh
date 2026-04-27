from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.document_service import DocumentService
from app.services.audit_service import AuditService
from app.core.locks import LockService
from app.api.dependencies import get_current_user
from app.models.user import User
from pydantic import BaseModel
from typing import Optional, List
import uuid
import json
from app.tasks.worker import dummy_polish_task
from app.models.document import AsyncTask, DocumentApprovalLog, Document, DocumentSnapshot
from app.core.enums import TaskType, TaskStatus, DocumentStatus, WorkflowNode
from app.core.redis import get_redis
from app.api.dependencies import ai_rate_limiter
from app.services.sip_service import SIPService
from sqlalchemy import select, or_
from datetime import datetime
from app.core.exceptions import DocumentLockedError, DocumentPermissionError, DocumentStateError

router = APIRouter()

class DocumentResponse(BaseModel):
    doc_id: str
    title: str
    content: Optional[str]
    status: str
    dept_id: Optional[int]
    creator_id: int
    ai_polished_content: Optional[str]
    draft_suggestion: Optional[str]
    reviewer_id: Optional[int]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ApplyPolishRequest(BaseModel):
    final_content: Optional[str] = None

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    status: Optional[DocumentStatus] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    docs = await DocumentService.list_documents(
        db, current_user.user_id, current_user.dept_id, current_user.role_level, status, page, page_size
    )
    return docs

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 权限校验：仅本人或科长及以上可删
    if doc.creator_id != current_user.user_id and current_user.role_level < 5:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    doc.is_deleted = True
    
    # 【级联修复】删除公文时释放关联锁
    redis_client = await get_redis()
    lock_key = f"lock:{doc_id}"
    await redis_client.delete(lock_key)
    
    await db.commit()
    
    # 【对齐修复】添加审计日志
    background_tasks.add_task(
        AuditService.write_audit_log,
        doc_id, 
        WorkflowNode.REVISION, # 借用
        current_user.user_id, 
        {"note": f"公文被软删除，操作人: {current_user.username}"}
    )
    
    return {"status": "success"}

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document_detail(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 【水平越权修复】三层隔离逻辑
    if doc.status == DocumentStatus.DRAFTING and doc.creator_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="无法访问他人的草稿")
    if doc.dept_id != current_user.dept_id and current_user.role_level < 99 and doc.creator_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="跨科室访问受限")
    
    # 【敏感信息保护修复】非起草人不暴露临时草稿建议
    data = DocumentResponse.model_validate(doc)
    if current_user.user_id != doc.creator_id:
        data.draft_suggestion = None
        
    return data

class AutoSaveRequest(BaseModel):
    content: Optional[str] = None
    draft_content: Optional[str] = None
    model_config = {"extra": "forbid"}

class InitRequest(BaseModel):
    title: str

@router.post("/init")
async def init_document(
    payload: InitRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        doc_id = await DocumentService.init_document(db, payload.title, current_user.user_id, current_user.dept_id)
        background_tasks.add_task(AuditService.write_audit_log, doc_id, WorkflowNode.DRAFTING, current_user.user_id, {"note": "初始化起草公文"})
        return {"doc_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{doc_id}/submit")
async def submit_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 【高优先级修复】Endpoint 级越权校验：仅起草人可以提交审批
    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.creator_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="只有公文起草人可以提交审批")

    try:
        doc_obj, tolerance_flag = await DocumentService.submit_document(db, doc_id, current_user.user_id)
        
        audit_note = "起草人提交审批"
        if tolerance_flag:
            audit_note += " (容忍过期锁)"
            
        background_tasks.add_task(AuditService.write_audit_log, doc_id, WorkflowNode.SUBMITTED, current_user.user_id, {"note": audit_note})
        return {"status": "success"}
    except DocumentLockedError as e:
        # 【对齐修复】审计锁释放失败
        background_tasks.add_task(
            AuditService.write_audit_log, 
            doc_id, WorkflowNode.SUBMITTED, current_user.user_id, 
            {"note": "提交时发现死锁或他人持锁", "error": str(e)}
        )
        raise HTTPException(status_code=409, detail=str(e))
    except (DocumentPermissionError, DocumentStateError) as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{doc_id}/revise")
async def revise_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        # 严格越权校验：仅起草人可唤醒修改
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc.creator_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="只有公文起草人可以执行驳回唤醒操作")
            
        result = await DocumentService.revise_document(db, doc_id, current_user.user_id, current_user.username)
        background_tasks.add_task(AuditService.write_audit_log, doc_id, WorkflowNode.REVISION, current_user.user_id, {"note": "起草人开始驳回修改"})
        return result
    except (DocumentLockedError, DocumentStateError) as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{doc_id}/auto-save")
async def auto_save_document(
    doc_id: str, 
    payload: AutoSaveRequest, 
    lock_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 1. 严格检查 Payload：禁止同时传递 content 和 draft_content
    payload_dict = payload.model_dump(exclude_unset=True)
    if "content" in payload_dict and "draft_content" in payload_dict:
        raise HTTPException(status_code=400, detail="Ambiguous payload")

    # 2. 校验锁持有权
    redis_client = await get_redis()
    lock_key = f"lock:{doc_id}"
    lock_data_raw = await redis_client.get(lock_key)
    if not lock_data_raw:
        raise HTTPException(status_code=409, detail="Lock expired")
    
    lock_data = json.loads(lock_data_raw)
    if lock_data.get("token") != lock_token or lock_data.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not the lock holder")

    try:
        # 【对齐修复】判断 content 是否显式存在且非 None (防 null 绕过)
        has_explicit_content = "content" in payload_dict and payload_dict["content"] is not None
        doc, changed = await DocumentService.auto_save(
            db, doc_id, payload.content, payload.draft_content, has_explicit_content
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 刷新对象以确保属性已加载且未过期（解决 async 环境下的 lazy load 问题）
        await db.refresh(doc)
        
        return {
            "status": "success", 
            "changed": changed, 
            "saved_at": doc.updated_at.isoformat() if doc.updated_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/format")
async def trigger_format(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 校验权限
    doc = await DocumentService.get_document(db, doc_id)
    if not doc or doc.creator_id != current_user.user_id:
        raise HTTPException(status_code=403)

    task_id = str(uuid.uuid4())
    new_task = AsyncTask(
        task_id=task_id,
        task_type=TaskType.FORMAT,
        doc_id=doc_id,
        creator_id=current_user.user_id,
        task_status=TaskStatus.QUEUED
    )
    db.add(new_task)
    await db.commit()

    # 派发 Celery 任务
    from app.tasks.worker import dummy_format_task
    dummy_format_task.apply_async(args=[doc_id], task_id=task_id)

    return {"task_id": task_id}


@router.get("/{doc_id}/snapshots")
async def list_snapshots(
    doc_id: str, 
    page: int = 1, 
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 权限检查：需符合详情页的权限屏障
    doc = await DocumentService.get_document(db, doc_id)
    if not doc or (doc.dept_id != current_user.dept_id and current_user.role_level < 99 and doc.creator_id != current_user.user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    stmt = select(DocumentSnapshot).where(DocumentSnapshot.doc_id == doc_id).order_by(DocumentSnapshot.created_at.desc()).offset((page-1)*page_size).limit(page_size)
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    return {"data": snapshots}

@router.post("/{doc_id}/snapshots")
async def create_manual_snapshot(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404)
    
    if doc.creator_id != current_user.user_id and current_user.role_level < 5:
        raise HTTPException(status_code=403)
        
    snapshot = DocumentSnapshot(
        doc_id=doc_id,
        content=doc.content or "",
        trigger_event="manual_backup",
        creator_id=current_user.user_id
    )
    db.add(snapshot)
    await db.commit()
    return {"status": "success", "snapshot_id": snapshot.snapshot_id}

@router.post("/{doc_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    doc_id: str, 
    snapshot_id: int,
    lock_token: str, # 【对齐修复】必须持锁才能恢复
    background_tasks: BackgroundTasks,
    confirm: str = Query(...), 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if confirm != "CONFIRMED":
        raise HTTPException(status_code=400, detail="必须明确确认恢复操作")

    # 1. 锁持有权强校验
    redis_client = await get_redis()
    lock_key = f"lock:{doc_id}"
    lock_data_raw = await redis_client.get(lock_key)
    if not lock_data_raw:
        raise HTTPException(status_code=409, detail="未持有编辑锁，无法恢复快照")
    
    lock_data = json.loads(lock_data_raw)
    if lock_data.get("token") != lock_token or lock_data.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="锁凭证不匹配")

    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404)
        
    if doc.creator_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only creator can restore")

    stmt = select(DocumentSnapshot).where(DocumentSnapshot.snapshot_id == snapshot_id, DocumentSnapshot.doc_id == doc_id)
    result = await db.execute(stmt)
    snapshot = result.scalars().first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
        
    # 1. 自动备份当前内容（容灾）
    safety_snapshot = DocumentSnapshot(
        doc_id=doc_id,
        content=doc.content or "",
        trigger_event="pre_restore_backup",
        creator_id=current_user.user_id
    )
    db.add(safety_snapshot)
    
    # 2. 覆盖正文
    doc.content = snapshot.content
    await db.commit()
    
    background_tasks.add_task(AuditService.write_audit_log, doc_id, WorkflowNode.REVISION, current_user.user_id, {"note": f"恢复快照 #{snapshot_id}"})
    
    return {"status": "success", "restored_content": doc.content}

@router.post("/{doc_id}/apply-polish")
async def apply_document_polish(
    doc_id: str, 
    payload: ApplyPolishRequest,
    lock_token: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 【对齐修复】必须校验锁凭证且必填
    redis_client = await get_redis()
    lock_key = f"lock:{doc_id}"
    lock_data_raw = await redis_client.get(lock_key)
    if not lock_data_raw:
         raise HTTPException(status_code=409, detail="Lock expired or not held")
    
    lock_data = json.loads(lock_data_raw)
    if lock_data.get("token") != lock_token or lock_data.get("user_id") != current_user.user_id:
         raise HTTPException(status_code=403, detail="Lock token mismatch")

    doc = await DocumentService.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404)
        
    # 【审计增强】判断是否用户修改后应用
    is_modified = payload.final_content is not None and payload.final_content != doc.ai_polished_content
    audit_note = "用户接受并修改后应用" if is_modified else "用户全盘接受 AI 建议"

    try:
        await DocumentService.apply_polish(db, doc_id, current_user.user_id, payload.final_content)
        background_tasks.add_task(AuditService.write_audit_log, doc_id, WorkflowNode.POLISH, current_user.user_id, {"note": audit_note})
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/discard-polish")
async def discard_document_polish(
    doc_id: str, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    doc = await DocumentService.get_document(db, doc_id)
    if doc.creator_id != current_user.user_id:
        raise HTTPException(status_code=403)
        
    try:
        await DocumentService.discard_polish(db, doc_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class PolishRequest(BaseModel):
    context_kb_ids: List[int] = []

@router.post("/{doc_id}/polish", dependencies=[Depends(ai_rate_limiter)])
async def trigger_polish(
    doc_id: str, 
    payload: PolishRequest,
    lock_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 校验锁持有权
    redis_client = await get_redis()
    lock_key = f"lock:{doc_id}"
    lock_data_raw = await redis_client.get(lock_key)
    if not lock_data_raw:
        raise HTTPException(status_code=409, detail="Must hold a lock to trigger AI polish")
    
    lock_data = json.loads(lock_data_raw)
    if lock_data.get("token") != lock_token or lock_data.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=403, detail="Lock token mismatch or not owner")

    task_id = str(uuid.uuid4())
    new_task = AsyncTask(
        task_id=task_id,
        task_type=TaskType.POLISH,
        doc_id=doc_id,
        creator_id=current_user.user_id,
        task_status=TaskStatus.QUEUED,
        input_params={"context_kb_ids": payload.context_kb_ids}
    )
    db.add(new_task)
    await db.commit()
    
    dummy_polish_task.apply_async(args=[doc_id], task_id=task_id)
    
    await redis_client.set(f"task_status:{task_id}", json.dumps({
        "progress": 0,
        "status": TaskStatus.QUEUED.value,
        "result": None
    }), ex=3600)
    
    return {"task_id": task_id}

@router.get("/{doc_id}/verify-sip")
async def verify_document_sip(
    doc_id: str, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    stmt = select(DocumentApprovalLog).where(
        DocumentApprovalLog.doc_id == doc_id, 
        DocumentApprovalLog.decision_status == "APPROVED"
    ).order_by(DocumentApprovalLog.reviewed_at.desc()).limit(1)
    
    res = await db.execute(stmt)
    log = res.scalars().first()
    
    if not log or not log.sip_hash:
        return {"is_valid": False, "message": "未找到该公文的有效审批存证记录"}
        
    doc_res = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = doc_res.scalars().first()
    
    if not doc:
        return {"is_valid": False, "message": "公文实体不存在"}
        
    current_hash = SIPService.generate_sip_fingerprint(doc.content, log.reviewer_id, log.reviewed_at)
    
    if current_hash == log.sip_hash:
        return {"is_valid": True, "message": "存证校验通过，内容未被篡改"}
    else:
        return {"is_valid": False, "message": "存证校验失败！内容可能已被篡改"}
