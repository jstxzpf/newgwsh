from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.document import Document
from app.models.knowledge import KnowledgeBaseHierarchy
from app.models.system import AsyncTask
from app.models.enums import DocumentStatus, TaskStatus
from app.core.config import settings
from sqlalchemy import select
import os
import json
from datetime import datetime

@celery_app.task(bind=True, max_retries=3)
def process_polish_task(self, task_id: str, doc_id: str):
    with SyncSessionLocal() as session:
        _mark_task_processing(session, task_id)
        try:
            # 真实 AI 推理逻辑应调用相关 Service，此处模拟
            result_content = "AI 润色结果建议稿..."

            # 铁律：跨进程状态二次复核 (P0 §七.3)
            with session.begin():
                doc = session.execute(select(Document).where(Document.doc_id == doc_id).with_for_update()).scalars().first()
                if not doc or doc.status != DocumentStatus.DRAFTING:
                    _mark_task_failed(session, task_id, "公文状态已变更，润色结果被废弃")
                    return
                
                doc.ai_polished_content = result_content
                _mark_task_completed(session, task_id, "success")
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
                kb_node = session.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == kb_id).with_for_update()).scalars().first()
                if not kb_node or kb_node.is_deleted:
                    if task_id: _mark_task_failed(session, task_id, "节点已被删除")
                    return
                
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

def _mark_task_failed(session, task_id, error):
    task = session.get(AsyncTask, task_id)
    if task:
        task.task_status = TaskStatus.FAILED
        task.error_message = error
        task.completed_at = datetime.now()