from celery import shared_task
from app.core.database import SyncSessionLocal
from app.models.document import Document
import time

@shared_task(name="app.tasks.worker.test_sync_db_task")
def test_sync_db_task():
    with SyncSessionLocal() as session:
        # 简单查询测试同步连接
        try:
            # 注意：如果表还没创建，这里可能会报错，这仅作为结构验证
            count = session.query(Document).count()
        except Exception:
            count = -1
        
        time.sleep(1)
        return {
            "status": "success",
            "document_count": count,
            "sync_mode": True,
            "timestamp": time.time()
        }
