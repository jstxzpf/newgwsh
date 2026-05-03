from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
import time

@celery_app.task(bind=True, max_retries=3)
def dummy_polish_task(self, task_id: str, doc_id: str):
    with SyncSessionLocal() as session:
        # 这里演示同步会话的使用
        print(f"Task {task_id} processing doc {doc_id}")
        time.sleep(2)
        return {"status": "success", "task_id": task_id}