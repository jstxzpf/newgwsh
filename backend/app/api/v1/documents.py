from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document, DocumentSnapshot, DocumentType
from app.models.system import NBSWorkflowAudit
from app.models.enums import WorkflowNodeId
from app.schemas.document import DocumentInitRequest, AutoSaveRequest, ApplyPolishRequest, SnapshotCreateRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.services.document_service import DocumentService
from app.services.lock_service import LockService
from app.core.locks import redis_client
import json

router = APIRouter()

@router.get("")
async def list_documents(
    status: str | None = None,
    dept_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Document).where(Document.is_deleted == False)
    
    # 权限隔离契约 (§二.2)
    if current_user.role_level >= 99:
        pass # 管理员可见全部
    elif current_user.role_level >= 5:
        query = query.where(Document.dept_id == current_user.dept_id)
    else:
        # 科员排除他人 DRAFTING 状态草稿
        from sqlalchemy import or_
        query = query.where(or_(
            Document.creator_id == current_user.user_id,
            Document.status != "DRAFTING"
        ))

    if status:
        query = query.where(Document.status == status)
    if dept_id:
        query = query.where(Document.dept_id == dept_id)

    # 统计总数
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    
    # 加入文种名称和起草人名称
    query = query.join(DocumentType, Document.doc_type_id == DocumentType.type_id) \
                 .join(SystemUser, Document.creator_id == SystemUser.user_id) \
                 .add_columns(DocumentType.type_name, SystemUser.full_name)
    
    result = await db.execute(query.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    items = result.all()
    
    return {
        "code": 200, 
        "message": "success", 
        "data": {
            "total": total,
            "items": [
                {
                    "doc_id": row.Document.doc_id,
                    "title": row.Document.title,
                    "status": row.Document.status,
                    "doc_type_name": row.type_name,
                    "creator_name": row.full_name,
                    "created_at": row.Document.created_at
                } for row in items
            ]
        }
    }

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Document.status, func.count()).where(Document.is_deleted == False)
    
    if current_user.role_level < 99:
        if current_user.role_level >= 5:
            query = query.where(Document.dept_id == current_user.dept_id)
        else:
            query = query.where(Document.creator_id == current_user.user_id)
            
    query = query.group_by(Document.status)
    result = await db.execute(query)
    counts = dict(result.all())
    
    # 还需要"我起草的"总数
    drafted_query = select(func.count()).where(Document.creator_id == current_user.user_id, Document.is_deleted == False)
    drafted_result = await db.execute(drafted_query)
    drafted_count = drafted_result.scalar() or 0
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "drafted": drafted_count,
            "submitted": counts.get("SUBMITTED", 0),
            "reviewed": counts.get("REVIEWED", 0),
            "rejected": counts.get("REJECTED", 0),
            "approved": counts.get("APPROVED", 0),
            "archived": counts.get("ARCHIVED", 0)
        }
    }

@router.post("/init")
async def init_document(req: DocumentInitRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc_id = await DocumentService.init_document(db, req.title, req.doc_type_id, current_user.user_id, current_user.dept_id)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"doc_id": doc_id}}

@router.get("/{doc_id}")
async def get_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Document, DocumentType.type_name, SystemUser.full_name) \
            .join(DocumentType, Document.doc_type_id == DocumentType.type_id) \
            .join(SystemUser, Document.creator_id == SystemUser.user_id) \
            .where(Document.doc_id == doc_id, Document.is_deleted == False)
            
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise BusinessException(404, "公文不存在")
        
    doc = row.Document
    return {
        "code": 200, 
        "message": "success", 
        "data": {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "content": doc.content,
            "status": doc.status,
            "doc_type_id": doc.doc_type_id,
            "doc_type_name": row.type_name,
            "creator_name": row.full_name,
            "ai_polished_content": doc.ai_polished_content,
            "draft_suggestion": doc.draft_suggestion
        }
    }

@router.post("/{doc_id}/auto-save")
async def auto_save(doc_id: str, req: AutoSaveRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc or doc.is_deleted:
        raise BusinessException(404, "公文不存在")
    if doc.status != "DRAFTING":
        raise BusinessException(409, "当前状态不可保存")
        
    await DocumentService.auto_save_draft(db, doc, req.title, req.content, req.draft_content)
    await db.commit()
    return {"code": 200, "message": "success", "data": None}

@router.post("/{doc_id}/submit")
async def submit_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    
    lock_key = f"lock:{doc_id}"
    lock_val = await redis_client.get(lock_key)
    if lock_val:
        lock_data = json.loads(lock_val)
        if lock_data.get("user_id") != current_user.user_id:
            raise BusinessException(409, "已有他人占锁，提交失败")
    else:
        if current_user.user_id != doc.creator_id and current_user.role_level < 99:
            raise BusinessException(403, "锁已释放且无权提交他人公文")

    log_id = await DocumentService.submit_document(db, doc, current_user.user_id)
    await redis_client.delete(lock_key)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"doc_id": doc_id, "status": "SUBMITTED", "log_id": log_id}}

@router.post("/{doc_id}/revise")
async def revise_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    
    res = await DocumentService.revise_document(db, doc, current_user.user_id, current_user.username)
    await db.commit()
    return {"code": 200, "message": "success", "data": res}

@router.post("/{doc_id}/apply-polish")
async def apply_polish(doc_id: str, req: ApplyPolishRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    
    await DocumentService.apply_polish(db, doc, req.final_content, current_user.user_id)
    await db.commit()
    return {"code": 200, "message": "success", "data": None}

@router.post("/{doc_id}/discard-polish")
async def discard_polish(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if doc:
        doc.ai_polished_content = None
        doc.draft_suggestion = None
        await db.commit()
    return {"code": 200, "message": "success", "data": None}

@router.get("/{doc_id}/snapshots")
async def list_snapshots(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentSnapshot).where(DocumentSnapshot.doc_id == doc_id).order_by(DocumentSnapshot.created_at.desc()))
    items = result.scalars().all()
    return {"code": 200, "message": "success", "data": {"items": [{"snapshot_id": s.snapshot_id, "content": s.content, "trigger_event": s.trigger_event, "created_at": s.created_at} for s in items]}}

@router.post("/{doc_id}/snapshots")
async def create_snapshot(doc_id: str, req: SnapshotCreateRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sid = await DocumentService.create_snapshot(db, doc_id, req.content, current_user.user_id, req.trigger_event)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"snapshot_id": sid}}

@router.delete("/{doc_id}")
async def delete_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    if current_user.user_id != doc.creator_id and current_user.role_level < 99:
        raise BusinessException(403, "无权删除他人公文")
    doc.is_deleted = True
    await redis_client.delete(f"lock:{doc_id}")
    await db.commit()
    return {"code": 200, "message": "success", "data": None}

@router.get("/{doc_id}/download")
async def download_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc or not doc.word_output_path:
        raise BusinessException(404, "排版文件尚未生成")
    from fastapi.responses import FileResponse
    return FileResponse(doc.word_output_path, media_type="application/octet-stream", filename=f"{doc.title}.docx")

@router.post("/{doc_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(doc_id: str, snapshot_id: int, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    snap_result = await db.execute(select(DocumentSnapshot).where(DocumentSnapshot.snapshot_id == snapshot_id, DocumentSnapshot.doc_id == doc_id))
    snap = snap_result.scalars().first()
    if not snap:
        raise BusinessException(404, "快照不存在")
    doc.content = snap.content

    audit = NBSWorkflowAudit(
        doc_id=doc_id,
        workflow_node_id=WorkflowNodeId.SNAPSHOT_RESTORE,
        operator_id=current_user.user_id,
        action_details={"snapshot_id": snapshot_id, "trigger_event": snap.trigger_event}
    )
    db.add(audit)
    await db.commit()
    return {"code": 200, "message": "success", "data": None}

@router.get("/{doc_id}/verify-sip")
async def verify_document_sip(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await DocumentService.verify_sip(db, doc_id)
    return {"code": 200, "message": "success", "data": res}


@router.post("/{doc_id}/archive")
async def archive_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """归档：APPROVED → ARCHIVED"""
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")

    await DocumentService.archive_document(db, doc, current_user.user_id)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"new_status": "ARCHIVED"}}


@router.post("/{doc_id}/dispatch")
async def dispatch_document(
    doc_id: str,
    dept_ids: list[int] = Body(..., embed=True),
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分发：记录分发科室 (APPROVED/ARCHIVED)"""
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")

    await DocumentService.dispatch_document(db, doc, current_user.user_id, dept_ids)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"dispatch_depts": doc.dispatch_depts}}


@router.get("/{doc_id}/number")
async def preview_document_number(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """预览发文编号（签发前预览，不实际分配）"""
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    if doc.document_number:
        return {"code": 200, "message": "success", "data": {"document_number": doc.document_number, "assigned": True}}

    preview = await DocumentService._generate_document_number(db)
    return {"code": 200, "message": "success", "data": {"document_number": preview, "assigned": False}}