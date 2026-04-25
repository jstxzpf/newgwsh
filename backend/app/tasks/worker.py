import time
import json
from app.core.celery_app import celery_app
from app.core.redis import redis_client
from app.core.database import SyncSessionLocal
from app.models.document import AsyncTask
from app.core.enums import TaskStatus

def update_task_progress(task_id: str, progress: int, status: TaskStatus, result: str = None):
    import redis
    from app.core.config import settings
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    r.set(f"task_status:{task_id}", json.dumps({
        "progress": progress,
        "status": status,
        "result": result
    }), ex=3600)
    
    # 同步更新数据库持久化
    db = SyncSessionLocal()
    try:
        db.query(AsyncTask).filter(AsyncTask.task_id == task_id).update({
            "progress_pct": progress,
            "task_status": status,
            "result_summary": result
        })
        db.commit()
    finally:
        db.close()

@celery_app.task(bind=True)
def dummy_polish_task(self, doc_id: str):
    task_id = self.request.id
    update_task_progress(task_id, 10, TaskStatus.PROCESSING)
    
    # 模拟 AI 推理耗时
    time.sleep(2)
    update_task_progress(task_id, 50, TaskStatus.PROCESSING)
    
    time.sleep(2)
    update_task_progress(task_id, 100, TaskStatus.COMPLETED, result="AI 润色建议内容预览...")

@celery_app.task(bind=True)
def parse_kb_file_task(self, kb_id: int, file_path: str):
    # Placeholder for Task 2
    pass
