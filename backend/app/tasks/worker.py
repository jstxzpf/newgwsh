import time
import json
import redis
from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.document import AsyncTask
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk
from app.core.enums import TaskStatus
from app.core.config import settings
from markitdown import MarkItDown

# 1. 建立单例同步 Redis 客户端供 Worker 使用，避免每次创建连接
sync_redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def update_task_progress(task_id: str, progress: int, status: TaskStatus, result: str = None, db_session=None):
    """
    更新任务进度。支持传入已存在的 db_session 以减少连接创建开销。
    """
    # 确保 status 序列化为字符串
    status_val = status.value if hasattr(status, 'value') else status
    
    sync_redis_client.set(f"task_status:{task_id}", json.dumps({
        "progress": progress,
        "status": status_val,
        "result": result
    }), ex=3600)
    
    db = db_session or SyncSessionLocal()
    try:
        db.query(AsyncTask).filter(AsyncTask.task_id == task_id).update({
            "progress_pct": progress,
            "task_status": status,
            "result_summary": result
        })
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if db_session is None: # 如果是自己创建的，则负责关闭
            db.close()

@celery_app.task(bind=True)
def dummy_polish_task(self, doc_id: str):
    task_id = self.request.id
    # 复用同一个 DB 会话
    with SyncSessionLocal() as db:
        update_task_progress(task_id, 10, TaskStatus.PROCESSING, db_session=db)
        
        time.sleep(2)
        update_task_progress(task_id, 50, TaskStatus.PROCESSING, db_session=db)
        
        time.sleep(2)
        update_task_progress(task_id, 100, TaskStatus.COMPLETED, result="AI 润色建议内容预览...", db_session=db)

@celery_app.task(bind=True)
def parse_kb_file_task(self, kb_id: int, file_path: str):
    task_id = self.request.id
    
    with SyncSessionLocal() as db:
        update_task_progress(task_id, 10, TaskStatus.PROCESSING, db_session=db)
        try:
            md = MarkItDown()
            result = md.convert(file_path)
            text_content = result.text_content
            update_task_progress(task_id, 50, TaskStatus.PROCESSING, db_session=db)
            
            chunk_size = 800
            chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
            
            node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
            if not node:
                raise ValueError(f"KB Node {kb_id} not found")
                
            for idx, chunk_text in enumerate(chunks):
                new_chunk = KnowledgeChunk(
                    kb_id=kb_id,
                    physical_file_id=node.physical_file_id,
                    chunk_index=idx,
                    content=chunk_text,
                    kb_tier=node.kb_tier,
                    security_level=node.security_level,
                    dept_id=node.dept_id, # 追加：同步科室属性
                    metadata_json={"source": "markitdown", "raw_length": len(chunk_text)}
                )
                db.add(new_chunk)
                
            node.parse_status = "READY"
            update_task_progress(task_id, 100, TaskStatus.COMPLETED, result=f"Parsed {len(chunks)} chunks", db_session=db)
            db.commit()
        except Exception as e:
            db.rollback()
            node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
            if node:
                node.parse_status = "FAILED"
                db.commit()
            update_task_progress(task_id, 0, TaskStatus.FAILED, result=str(e), db_session=db)
            raise e
