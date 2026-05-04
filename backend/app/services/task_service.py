from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.system import AsyncTask
from app.models.document import Document
from app.core.exceptions import BusinessException
from app.tasks.worker import dummy_polish_task
import uuid

class TaskService:
    @staticmethod
    async def trigger_polish_task(db: AsyncSession, doc_id: str, creator_id: int, input_params: dict) -> str:
        # 幂等拦截
        result = await db.execute(select(AsyncTask).where(
            AsyncTask.doc_id == doc_id, 
            AsyncTask.task_type == "POLISH",
            AsyncTask.task_status.in_(["QUEUED", "PROCESSING"])
        ))
        existing_task = result.scalars().first()
        if existing_task:
            return existing_task.task_id

        doc_result = await db.execute(select(Document).where(Document.doc_id == doc_id))
        doc = doc_result.scalars().first()
        if not doc or doc.status != "DRAFTING":
            raise BusinessException(409, "当前状态不可润色")

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
        dummy_polish_task.delay(task_id, doc_id)
        return task_id