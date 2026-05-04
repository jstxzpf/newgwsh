from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document, DocumentSnapshot
from app.schemas.document import DocumentInitRequest, AutoSaveRequest, ApplyPolishRequest, SnapshotCreateRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.services.document_service import DocumentService
from app.services.lock_service import LockService

router = APIRouter()

@router.get("/")
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

    # 分页
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()
    
    return {
        "code": 200, 
        "message": "success", 
        "data": {
            "total": total,
            "items": [
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "status": doc.status,
                    "created_at": doc.created_at
                } for doc in items
            ]
        }
    }

@router.post("/init")
async def init_document(req: DocumentInitRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc_id = await DocumentService.init_document(db, req.title, req.doc_type_id, current_user.user_id, current_user.dept_id)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"doc_id": doc_id}}

@router.get("/{doc_id}")
async def get_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    return {
        "code": 200, 
        "message": "success", 
        "data": {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "content": doc.content,
            "status": doc.status,
            "doc_type_id": doc.doc_type_id,
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
    
    await DocumentService.submit_document(db, doc, current_user.user_id)
    # 提交后自动释放锁
    await LockService.release_lock(db, doc_id, current_user.user_id, token="") # 逻辑内部会检查
    await db.commit()
    return {"code": 200, "message": "success", "data": {"doc_id": doc_id, "status": "SUBMITTED"}}

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

from sqlalchemy import func