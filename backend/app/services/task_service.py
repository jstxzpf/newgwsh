from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.system import AsyncTask
from app.models.document import Document
from app.core.exceptions import BusinessException
from app.tasks.worker import process_polish_task, process_format_task, process_parse_task
import uuid

class TaskService:
    @staticmethod
    async def trigger_polish_task(db: AsyncSession, doc_id: str, creator_id: int, input_params: dict) -> str:
        # 锁住文档行以串行化并发润色请求（防止幂等检查竞态）
        doc_result = await db.execute(
            select(Document).where(Document.doc_id == doc_id).with_for_update()
        )
        doc = doc_result.scalars().first()
        if not doc or doc.status != "DRAFTING":
            raise BusinessException(409, "当前状态不可润色")

        # 幂等拦截（在文档行锁保护下安全）
        result = await db.execute(select(AsyncTask).where(
            AsyncTask.doc_id == doc_id,
            AsyncTask.task_type == "POLISH",
            AsyncTask.task_status.in_(["QUEUED", "PROCESSING"])
        ))
        existing_task = result.scalars().first()
        if existing_task:
            return existing_task.task_id

        task_id = str(uuid.uuid4())
        new_task = AsyncTask(
            task_id=task_id,
            task_type="POLISH",
            doc_id=doc_id,
            creator_id=creator_id,
            input_params=input_params
        )
        db.add(new_task)

        # 派发 Celery
        process_polish_task.delay(task_id, doc_id)
        return task_id

    @staticmethod
    async def trigger_format_task(db: AsyncSession, doc_id: str, user_id: int, role_level: int) -> str:
        doc_result = await db.execute(select(Document).where(Document.doc_id == doc_id))
        doc = doc_result.scalars().first()
        if not doc or doc.status not in ["DRAFTING", "APPROVED"]:
            raise BusinessException(400, "仅允许对起草中或已通过的公文触发排版")

        # 属主校验：仅文档起草人或管理员可触发排版
        if doc.creator_id != user_id and role_level < 99:
            raise BusinessException(403, "仅公文起草人或管理员可触发排版")

        task_id = str(uuid.uuid4())
        new_task = AsyncTask(
            task_id=task_id, task_type="FORMAT", doc_id=doc_id, creator_id=user_id,
            input_params={"doc_id": doc_id}
        )
        db.add(new_task)
        process_format_task.delay(doc_id, task_id)
        return task_id

    @staticmethod
    async def retry_failed_task(db: AsyncSession, task_id: str):
        result = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
        task = result.scalars().first()
        if not task or task.task_status != "FAILED" or task.retry_count >= 3:
            raise BusinessException(400, "该任务不可重试")
        
        task.task_status = "QUEUED"
        task.retry_count += 1
        
        if task.task_type == "POLISH":
            process_polish_task.delay(task.task_id, task.doc_id)
        elif task.task_type == "FORMAT":
            process_format_task.delay(task.doc_id, task.task_id)
        elif task.task_type == "PARSE":
            process_parse_task.delay(task.kb_id, task.task_id)