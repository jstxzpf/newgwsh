from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.models.org import SystemUser
from app.models.document import Document, DocStatus
from app.models.task import AsyncTask, TaskType, TaskStatus
from app.schemas.response import StandardResponse, success, error
from app.tasks.worker import polish_document, format_document
from app.core.locks import lock_manager

router = APIRouter()

@router.post("/format", response_model=StandardResponse)
async def trigger_format(
    doc_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_active_user)
) -> Any:
    """手动触发排版任务 (P4.2)"""
    # 权限校验: 特权 (管理员或负责人)
    if current_user.role_level < 5:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    doc = await db.get(Document, doc_id)
    if not doc or doc.status not in [DocStatus.DRAFTING, DocStatus.APPROVED]:
        return error(code=409, message="Only DRAFTING or APPROVED documents can be formatted")

    task = format_document.delay(doc_id)
    await lock_manager.redis.set(f"task_owner:{task.id}", str(current_user.user_id), ex=3600)

    new_task = AsyncTask(
        task_id=task.id,
        task_type=TaskType.FORMAT,
        creator_id=current_user.user_id,
        doc_id=doc_id
    )
    db.add(new_task)
    await db.commit()
    return success(data={"task_id": task.id})

@router.post("/{task_id}/retry", response_model=StandardResponse)
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_admin_user)
) -> Any:
    """重试失败的任务 (P4.4)"""
    stmt = select(AsyncTask).where(AsyncTask.task_id == task_id)
    task_record = (await db.execute(stmt)).scalar_one_or_none()

    if not task_record:
        return error(code=404, message="Task not found")
    
    if task_record.task_status != TaskStatus.FAILED:
        return error(code=400, message="Only failed tasks can be retried")
        
    if task_record.retry_count >= 3:
        return error(code=400, message="Max retry count reached")

    # 根据类型重新派发
    if task_record.task_type == TaskType.POLISH:
        params = task_record.input_params or {}
        new_task = polish_document.delay(
            task_record.doc_id, 
            params.get("context_kb_ids", []), 
            params.get("exemplar_id")
        )
    elif task_record.task_type == TaskType.FORMAT:
        new_task = format_document.delay(task_record.doc_id)
    elif task_record.task_type == TaskType.PARSE:
        from app.tasks.worker import parse_knowledge
        new_task = parse_knowledge.delay(task_record.kb_id)
    else:
        return error(code=400, message="Unknown task type")

    # 更新旧记录或创建新记录? 契约说返回 task_id，通常派发新任务
    await lock_manager.redis.set(f"task_owner:{new_task.id}", str(current_user.user_id), ex=3600)
    
    # 增加重试计数并标记为 QUEUED
    task_record.retry_count += 1
    task_record.task_status = TaskStatus.QUEUED
    task_record.task_id = new_task.id # 更新 ID 以匹配新任务
    await db.commit()

    return success(data={"task_id": new_task.id})

@router.post("/polish", response_model=StandardResponse)
async def trigger_polish(
    doc_id: str,
    lock_token: str,
    context_kb_ids: List[int] = [],
    context_snapshot_version: Optional[int] = None,
    exemplar_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_active_user)
) -> Any:
    """触发 AI 润色任务 (P4.1, 实施约束规则 1)"""
    
    # 1. 锁校验 (实施约束规则 1: 锁持有者权限)
    is_locked = await lock_manager.verify_lock(doc_id, lock_token)
    if not is_locked:
        return error(code=423, message="Valid lock_token required to trigger polish")
    
    # 2. 状态校验 (实施约束规则 3)
    doc = await db.get(Document, doc_id)
    if not doc or doc.status != DocStatus.DRAFTING:
        return error(code=409, message="Document must be in DRAFTING status")

    # 3. 派发 Celery 任务
    task = polish_document.delay(doc_id, context_kb_ids, exemplar_id)
    
    # 4. 存储任务归属到 Redis (用于 SSE 鉴权 P4.1)
    await lock_manager.redis.set(f"task_owner:{task.id}", str(current_user.user_id), ex=3600)
    
    # 5. 持久化记录
    new_task = AsyncTask(
        task_id=task.id,
        task_type=TaskType.POLISH,
        creator_id=current_user.user_id,
        doc_id=doc_id,
        input_params={
            "context_kb_ids": context_kb_ids,
            "context_snapshot_version": context_snapshot_version,
            "exemplar_id": exemplar_id,
            "lock_token": lock_token
        }
    )
    db.add(new_task)
    await db.commit()
    
    return success(data={"task_id": task.id})

@router.get("/{task_id}", response_model=StandardResponse)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: SystemUser = Depends(deps.get_current_user)
) -> Any:
    """查询任务状态 (P4.3)"""
    stmt = select(AsyncTask).where(AsyncTask.task_id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        return error(code=404, message="Task not found")
        
    return success(data=task)
