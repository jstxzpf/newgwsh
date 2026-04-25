import time
import json
from app.core.celery_app import celery_app
from app.core.redis import redis_client
from app.core.database import SyncSessionLocal
from app.models.document import AsyncTask
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk
from app.core.enums import TaskStatus
from markitdown import MarkItDown

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
    task_id = self.request.id
    update_task_progress(task_id, 10, TaskStatus.PROCESSING)
    
    db = SyncSessionLocal()
    try:
        # 1. 提取文本
        md = MarkItDown()
        result = md.convert(file_path)
        text_content = result.text_content
        update_task_progress(task_id, 50, TaskStatus.PROCESSING)
        
        # 2. 模拟切片 (简单按长度)
        chunk_size = 800
        chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
        
        # 获取节点信息
        node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
        if not node:
            raise ValueError("KB Node not found")
            
        # 3. 入库 chunks
        for idx, chunk_text in enumerate(chunks):
            new_chunk = KnowledgeChunk(
                kb_id=kb_id,
                physical_file_id=node.physical_file_id,
                chunk_index=idx,
                content=chunk_text,
                kb_tier=node.kb_tier,
                security_level=node.security_level,
                metadata_json={"source": "markitdown", "raw_length": len(chunk_text)}
            )
            db.add(new_chunk)
            
        # 4. 更新节点状态
        node.parse_status = "READY"
        db.commit()
        
        update_task_progress(task_id, 100, TaskStatus.COMPLETED, result=f"Parsed {len(chunks)} chunks")
    except Exception as e:
        db.rollback()
        # 更新节点状态为失败
        node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
        if node:
            node.parse_status = "FAILED"
            db.commit()
        update_task_progress(task_id, 0, TaskStatus.FAILED, result=str(e))
        raise e
    finally:
        db.close()
