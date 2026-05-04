from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.document import Document
from app.models.system import AsyncTask
from app.models.enums import DocumentStatus, TaskStatus
from sqlalchemy import select
import time
import json

@celery_app.task(bind=True, max_retries=3)
def process_polish_task(self, task_id: str, doc_id: str):
    with SyncSessionLocal() as session:
        # 1. 标记任务开始
        task = session.get(AsyncTask, task_id)
        if task:
            task.task_status = TaskStatus.PROCESSING
            task.started_at = time.strftime('%Y-%m-%d %H:%M:%S')
            session.commit()

        try:
            # 模拟 AI 耗时处理
            print(f"Task {task_id} AI polishing doc {doc_id}...")
            time.sleep(5)
            polish_result = f"这是对公文 {doc_id} 的 AI 润色建议内容..."

            # 2. 关键：跨进程状态二次复核铁律 (P0)
            # 使用 SELECT ... FOR UPDATE 加锁读取
            with session.begin():
                result = session.execute(
                    select(Document).where(Document.doc_id == doc_id).with_for_update()
                )
                doc = result.scalars().first()
                
                if not doc:
                    raise Exception("公文不存在")
                
                # POLISH 任务：校验 status == DRAFTING
                if doc.status != DocumentStatus.DRAFTING:
                    # 状态已变更，放弃写入
                    task = session.get(AsyncTask, task_id)
                    task.task_status = TaskStatus.FAILED
                    task.error_message = "公文状态已变更，润色结果被废弃"
                    task.result_summary = json.dumps({"result": "ABORTED", "reason": f"status={doc.status}"})
                    return {"status": "aborted", "reason": "status_changed"}

                # 复核通过，写入结果
                doc.ai_polished_content = polish_result
                
                # 更新任务状态
                task = session.get(AsyncTask, task_id)
                task.task_status = TaskStatus.COMPLETED
                task.progress_pct = 100
                task.completed_at = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 发布 Redis 通知略（实际应通过 PubSub 推送至 SSE）
            return {"status": "success", "task_id": task_id}

        except Exception as e:
            session.rollback()
            task = session.get(AsyncTask, task_id)
            if task:
                task.task_status = TaskStatus.FAILED
                task.error_message = str(e)
                session.commit()
            raise self.retry(exc=e)