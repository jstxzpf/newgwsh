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
from markdown_it import MarkdownIt

# 1. 建立单例同步 Redis 客户端供 Worker 使用，避免每次创建连接
sync_redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def update_task_progress(task_id: str, progress: int, status: TaskStatus, result: str = None, db_session=None):
    """
    更新任务进度。支持传入已存在的 db_session 以减少连接创建开销。
    """
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
        if db_session is None: 
            db.close()

@celery_app.task(bind=True)
def dummy_polish_task(self, doc_id: str):
    task_id = self.request.id
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
            # 1. 降维提取纯文本 (保留 MarkItDown 获取基底)
            md_converter = MarkItDown()
            result = md_converter.convert(file_path)
            text_content = result.text_content
            update_task_progress(task_id, 50, TaskStatus.PROCESSING, db_session=db)
            
            # 2. 方案强制对齐：使用 markdown-it-py 进行 AST 语义切片
            md = MarkdownIt()
            tokens = md.parse(text_content)
            
            chunks = []
            current_chunk = []
            current_path = [] # 记录标题路径
            
            for token in tokens:
                if token.type == 'heading_open':
                    level = int(token.tag[1:])
                    # 保存上一个 chunk
                    if current_chunk:
                        chunks.append({
                            "text": "\n".join(current_chunk),
                            "path": " | ".join(current_path)
                        })
                        current_chunk = []
                    # 更新路径栈
                    current_path = current_path[:level-1]
                elif token.type == 'inline':
                    # 如果刚才开了 heading，更新标题路径
                    # 简单探测上一个 token 是否为当前 level 的 heading_open
                    prev_token = tokens[tokens.index(token)-1] if tokens.index(token) > 0 else None
                    if prev_token and prev_token.type == 'heading_open':
                        current_path.append(token.content)
                    else:
                        current_chunk.append(token.content)
                elif token.type in ['paragraph_close', 'table_close']:
                    current_chunk.append("\n")

            # 最后一个 chunk
            if current_chunk:
                chunks.append({
                    "text": "\n".join(current_chunk).strip(),
                    "path": " | ".join(current_path)
                })
                
            # 清理空 chunk，并应用单切片内超长（800）的次级切分保护
            final_chunks = []
            for c in chunks:
                if not c["text"]: continue
                text_part = c["text"]
                if len(text_part) > 800:
                    sub_chunks = [text_part[i:i+800] for i in range(0, len(text_part), 800)]
                    for sc in sub_chunks:
                        final_chunks.append({"text": sc, "path": c["path"]})
                else:
                    final_chunks.append(c)
            
            node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
            if not node:
                raise ValueError(f"KB Node {kb_id} not found")
                
            for idx, c_data in enumerate(final_chunks):
                new_chunk = KnowledgeChunk(
                    kb_id=kb_id,
                    physical_file_id=node.physical_file_id,
                    chunk_index=idx,
                    content=c_data["text"],
                    kb_tier=node.kb_tier,
                    security_level=node.security_level,
                    dept_id=node.dept_id,
                    # 方案强制对齐：将标题路径强制注入 meta
                    metadata_json={"source": "markitdown+ast", "heading_path": c_data["path"]}
                )
                db.add(new_chunk)
                
            node.parse_status = "READY"
            update_task_progress(task_id, 100, TaskStatus.COMPLETED, result=f"AST Parsed {len(final_chunks)} chunks", db_session=db)
            db.commit()
        except Exception as e:
            db.rollback()
            node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
            if node:
                node.parse_status = "FAILED"
                db.commit()
            update_task_progress(task_id, 0, TaskStatus.FAILED, result=str(e), db_session=db)
            raise e
