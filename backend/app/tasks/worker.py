from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.document import Document
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk
from app.models.system import AsyncTask
from app.models.enums import DocumentStatus, TaskStatus
from app.core.config import settings
from app.core.ollama_client import generate_sync
from sqlalchemy import select
import os
import json
import redis
from datetime import datetime

sync_redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

_POLISH_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "polish_system.txt")

@celery_app.task(bind=True, max_retries=3)
def process_polish_task(self, task_id: str, doc_id: str):
    with SyncSessionLocal() as session:
        _mark_task_processing(session, task_id)
        try:
            # 1. 加载公文与任务参数（单独事务，不长时间持锁）
            with session.begin():
                doc = session.execute(
                    select(Document).where(Document.doc_id == doc_id).with_for_update()
                ).scalars().first()

                if not doc or doc.status != DocumentStatus.DRAFTING:
                    _mark_task_failed(session, task_id, "公文状态已变更，润色结果被废弃")
                    return

                doc_content = doc.content or ""

                task = session.get(AsyncTask, task_id)
                input_params = task.input_params if task else {}
                context_kb_ids = input_params.get("context_kb_ids", [])
                exemplar_id = input_params.get("exemplar_id")

                # 加载知识库上下文
                context_parts = []
                if context_kb_ids:
                    chunks = session.execute(
                        select(KnowledgeChunk).where(
                            KnowledgeChunk.kb_id.in_(context_kb_ids),
                            KnowledgeChunk.is_deleted == False
                        ).limit(10)
                    ).scalars().all()
                    for c in chunks:
                        context_parts.append(f"[来源: {c.metadata_json.get('title_path', '未知')}]\n{c.content}")

                # 加载范文
                if exemplar_id:
                    from app.models.document import ExemplarDocument
                    exemplar = session.get(ExemplarDocument, exemplar_id)
                    if exemplar and exemplar.extracted_text:
                        context_parts.insert(0, f"[参考范文: {exemplar.title}]\n{exemplar.extracted_text}")

                context_str = "\n\n".join(context_parts) if context_parts else "无额外参考上下文"

            # 2. 构建 Prompt（事务外）
            if os.path.exists(_POLISH_PROMPT_PATH):
                with open(_POLISH_PROMPT_PATH, "r", encoding="utf-8") as f:
                    template = f.read()
            else:
                template = "请润色以下公文：\n{content}\n\n参考上下文：{context}\n\n润色后正文："

            prompt = template.format(content=doc_content, context=context_str)

            # 3. 调用 Ollama（事务外，不持数据库锁）
            _publish_progress(task_id, 30, "正在调用 AI 模型...")
            try:
                polished = generate_sync(prompt)
            except Exception as llm_err:
                _mark_task_failed(session, task_id, f"AI 引擎调用失败: {str(llm_err)}")
                return

            if not polished or not polished.strip():
                _mark_task_failed(session, task_id, "AI 引擎返回空结果")
                return

            _publish_progress(task_id, 90, "正在保存结果...")

            # 4. 铁律：跨进程状态二次复核 + 保存（新事务 + 行锁）
            with session.begin():
                doc = session.execute(
                    select(Document).where(Document.doc_id == doc_id).with_for_update()
                ).scalars().first()
                if not doc or doc.status != DocumentStatus.DRAFTING:
                    _mark_task_failed(session, task_id, "公文状态已变更，润色结果被废弃")
                    return

                doc.ai_polished_content = polished
                doc.draft_suggestion = polished
                _mark_task_completed(session, task_id, polished[:200])

        except Exception as e:
            session.rollback()
            raise self.retry(exc=e)

@celery_app.task(bind=True, max_retries=3)
def process_format_task(self, doc_id: str, task_id: str = None):
    with SyncSessionLocal() as session:
        if task_id: _mark_task_processing(session, task_id)
        try:
            os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(settings.OUTPUT_DIR, f"{doc_id}.docx")

            # 铁律：跨进程状态二次复核 (P0 §七.3)
            with session.begin():
                doc = session.execute(select(Document).where(Document.doc_id == doc_id).with_for_update()).scalars().first()
                if not doc or doc.status != DocumentStatus.APPROVED:
                    if task_id: _mark_task_failed(session, task_id, "公文未处于已通过状态")
                    return
                
                doc.word_output_path = output_path
                if task_id: _mark_task_completed(session, task_id, output_path)
        except Exception as e:
            session.rollback()
            raise self.retry(exc=e)

@celery_app.task(bind=True, max_retries=3)
def process_parse_task(self, kb_id: int, task_id: str = None):
    with SyncSessionLocal() as session:
        if task_id: _mark_task_processing(session, task_id)
        try:
            # 真实解析逻辑应调用 ast_chunker
            
            # 铁律：跨进程状态二次复核 (P0 §七.3)
            with session.begin():
                from app.models.knowledge import KnowledgeChunk
                from sqlalchemy import text
                
                kb_node = session.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == kb_id).with_for_update()).scalars().first()
                if not kb_node or kb_node.is_deleted:
                    if task_id: _mark_task_failed(session, task_id, "节点已被删除")
                    return
                
                # 模拟生成切片
                from app.models.knowledge import KnowledgePhysicalFile
                physical_file = session.get(KnowledgePhysicalFile, kb_node.physical_file_id)
                content = "模拟切片内容"
                if physical_file and os.path.exists(physical_file.storage_path):
                    try:
                        with open(physical_file.storage_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except:
                        pass

                chunk = KnowledgeChunk(
                    kb_id=kb_node.kb_id,
                    content=content,
                    security_level=kb_node.security_level,
                    metadata_json={"title_path": kb_node.node_name},
                    embedding=None # 模拟向量
                )
                session.add(chunk)
                
                kb_node.parse_status = "READY"
                if task_id: _mark_task_completed(session, task_id, "parsed")
        except Exception as e:
            session.rollback()
            raise self.retry(exc=e)

def _mark_task_processing(session, task_id):
    task = session.get(AsyncTask, task_id)
    if task:
        task.task_status = TaskStatus.PROCESSING
        task.started_at = datetime.now()
        session.commit()

def _mark_task_completed(session, task_id, summary):
    task = session.get(AsyncTask, task_id)
    if task:
        task.task_status = TaskStatus.COMPLETED
        task.progress_pct = 100
        task.result_summary = summary
        task.completed_at = datetime.now()
        session.commit()
        sync_redis.publish(f"task_events:{task_id}", json.dumps({"event": "task.completed", "task_id": task_id, "result_summary": summary}))

def _mark_task_failed(session, task_id, error):
    task = session.get(AsyncTask, task_id)
    if task:
        task.task_status = TaskStatus.FAILED
        task.error_message = error
        task.completed_at = datetime.now()
        session.commit()
        sync_redis.publish(f"task_events:{task_id}", json.dumps({"event": "task.failed", "task_id": task_id, "error_message": error}))

def _publish_progress(task_id, pct, message):
    sync_redis.publish(f"task_events:{task_id}", json.dumps({
        "event": "task.progress",
        "task_id": task_id,
        "progress_pct": pct,
        "message": message,
    }))