import os
import time
import json
import subprocess
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy import select, text
from sqlalchemy.orm import joinedload
from app.core.database import SyncSessionLocal
from app.models.document import Document, DocStatus, ExemplarDocument
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk
from app.services.ai_service import ai_service
from app.core.config import settings
from app.core.locks import lock_manager

def publish_event(task_id: str, event_type: str, data: dict):
    """向 Redis Pub/Sub 发送事件"""
    import redis
    r = redis.from_url(settings.REDIS_URL)
    payload = {
        "event": event_type,
        "data": data
    }
    r.publish(f"task_channel:{task_id}", json.dumps(payload))

@shared_task(name="app.tasks.worker.parse_knowledge")
def parse_knowledge(kb_id: int, task_id: str = None):
    """
    异步解析知识库文件: MarkItDown -> AST Chunk -> Embedding -> SQL
    """
    with SyncSessionLocal() as session:
        node = session.get(KnowledgeBaseHierarchy, kb_id)
        if not node or node.is_deleted or not node.physical_file_id:
            if task_id: publish_event(task_id, "task.failed", {"error": "Node not found or deleted"})
            return "Node not found or deleted"
        
        from app.models.knowledge import KnowledgePhysicalFile
        phys = session.get(KnowledgePhysicalFile, node.physical_file_id)
        if not phys:
             if task_id: publish_event(task_id, "task.failed", {"error": "Physical file record not found"})
             return "Physical file record not found"

        node.parse_status = "PARSING"
        session.commit()
        if task_id: publish_event(task_id, "task.progress", {"progress_pct": 10})
        
        try:
            abs_path = os.path.join(settings.STORAGE_ROOT, phys.file_path)
            md_content = ai_service.parse_to_markdown(abs_path)
            if task_id: publish_event(task_id, "task.progress", {"progress_pct": 30})
            
            chunks = ai_service.chunk_markdown(md_content)
            
            for i, chunk_data in enumerate(chunks):
                vector = ai_service.get_embedding(chunk_data["content"])
                new_chunk = KnowledgeChunk(
                    kb_id=node.kb_id,
                    physical_file_id=node.physical_file_id,
                    content=chunk_data["content"],
                    embedding=vector,
                    metadata_json=chunk_data["metadata"],
                    kb_tier=node.kb_tier,
                    security_level=node.security_level,
                    dept_id=node.dept_id,
                    owner_id=node.owner_id,
                    is_deleted=False
                )
                session.add(new_chunk)
                if task_id:
                    progress = 30 + int((i + 1) / len(chunks) * 60)
                    publish_event(task_id, "task.progress", {"progress_pct": progress})

            node.parse_status = "READY"
            session.commit()
            if task_id: publish_event(task_id, "task.completed", {"kb_id": kb_id})
            return f"Parsed {len(chunks)} chunks"
        except Exception as e:
            node.parse_status = "FAILED"
            session.commit()
            if task_id: publish_event(task_id, "task.failed", {"error": str(e)})
            return f"Error: {str(e)}"

@shared_task(name="app.tasks.worker.polish_document", bind=True)
def polish_document(self, doc_id: str, context_kb_ids: list, exemplar_id: int = None):
    """
    异步 AI 润色任务 (含二次状态复核 P0 铁律)
    """
    task_id = self.request.id
    publish_event(task_id, "task.progress", {"progress_pct": 10})
    
    with SyncSessionLocal() as session:
        # 1. 预检读取
        doc = session.execute(
            select(Document).options(joinedload(Document.doc_type)).where(Document.doc_id == doc_id)
        ).scalar_one_or_none()
        
        if not doc:
            publish_event(task_id, "task.failed", {"error": "Document not found"})
            return "Document not found"
            
        if doc.status != DocStatus.DRAFTING:
            msg = f"ABORTED: Document status is {doc.status.name}, expected DRAFTING"
            publish_event(task_id, "task.failed", {"error": msg})
            return msg
        
        # 2. 检索挂载上下文 (RAG)
        context_text = ""
        if context_kb_ids:
            stmt = select(KnowledgeChunk).where(
                KnowledgeChunk.kb_id.in_(context_kb_ids),
                KnowledgeChunk.is_deleted == False,
                KnowledgeChunk.security_level != 3 # CORE
            ).limit(10)
            chunks = session.execute(stmt).scalars().all()
            context_text = "\n\n".join([f"来源: {c.metadata_json.get('title_path')}\n内容: {c.content}" for c in chunks])
        
        publish_event(task_id, "task.progress", {"progress_pct": 40})
        
        # 3. 获取范文文本 (Few-shot)
        exemplar_text = ""
        if exemplar_id:
            exemplar = session.get(ExemplarDocument, exemplar_id)
            if exemplar and not exemplar.is_deleted:
                exemplar_text = exemplar.extracted_text or ""

        content_to_polish = doc.content or ""
        doc_type_name = doc.doc_type.type_name if doc.doc_type else "通用公文"

    # 4. 调用 LLM
    try:
        polished_text = ai_service.chat_completion(
            "system_polish", 
            content_to_polish, 
            context=context_text,
            exemplar_text=exemplar_text,
            doc_type_name=doc_type_name
        )
        
        publish_event(task_id, "task.progress", {"progress_pct": 90})
        
        # 5. 写入阶段: 二次复核 (FOR UPDATE)
        with SyncSessionLocal() as session:
            doc_locked = session.execute(
                select(Document).where(Document.doc_id == doc_id).with_for_update()
            ).scalar_one_or_none()
            
            if doc_locked and doc_locked.status == DocStatus.DRAFTING:
                doc_locked.ai_polished_content = polished_text
                session.commit()
                publish_event(task_id, "task.completed", {"doc_id": doc_id})
                return "Polishing completed"
            else:
                current_status = doc_locked.status.name if doc_locked else "DELETED"
                msg = f"ABORTED: Final status check failed ({current_status})"
                publish_event(task_id, "task.failed", {"error": msg})
                return msg
    except Exception as e:
        publish_event(task_id, "task.failed", {"error": str(e)})
        return f"Error: {str(e)}"

@shared_task(name="app.tasks.worker.format_document", bind=True)
def format_document(self, doc_id: str):
    """
    异步公文排版任务 (含状态复核 P0 铁律)
    """
    task_id = self.request.id
    publish_event(task_id, "task.progress", {"progress_pct": 10})
    
    with SyncSessionLocal() as session:
        # 1. 预检读取
        doc = session.execute(
            select(Document).options(joinedload(Document.doc_type)).where(Document.doc_id == doc_id)
        ).scalar_one_or_none()
        
        if not doc:
            publish_event(task_id, "task.failed", {"error": "Document not found"})
            return "Document not found"
            
        # 2. 状态复核: 必须是 APPROVED
        if doc.status != DocStatus.APPROVED:
            msg = f"ABORTED: Document status is {doc.status.name}, expected APPROVED"
            publish_event(task_id, "task.failed", {"error": msg})
            return msg
        
        content_md = doc.content or ""
        layout_rules = doc.doc_type.layout_rules if doc.doc_type else {}

    try:
        # 3. 执行物理排版
        from app.services.docx_service import docx_service
        output_filename = f"document_{doc_id}_{int(time.time())}.docx"
        output_path = os.path.join(settings.STORAGE_ROOT, "outputs", output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        publish_event(task_id, "task.progress", {"progress_pct": 50})
        res = docx_service.format_document(content_md, output_path, layout_rules)
        publish_event(task_id, "task.progress", {"progress_pct": 90})
            
        # 4. 写入阶段: 二次复核 (FOR UPDATE)
        with SyncSessionLocal() as session:
            doc_locked = session.execute(
                select(Document).where(Document.doc_id == doc_id).with_for_update()
            ).scalar_one_or_none()
            
            if doc_locked and doc_locked.status == DocStatus.APPROVED:
                doc_locked.word_output_path = output_path
                session.commit()
                publish_event(task_id, "task.completed", {
                    "doc_id": doc_id, 
                    "file_path": output_path,
                    "warnings": res.get("warnings", [])
                })
                return f"Formatting completed: {output_path}"
            else:
                current_status = doc_locked.status.name if doc_locked else "DELETED"
                msg = f"ABORTED: Final status check failed ({current_status})"
                publish_event(task_id, "task.failed", {"error": msg})
                return msg
    except Exception as e:
        publish_event(task_id, "task.failed", {"error": str(e)})
        return f"Error: {str(e)}"

@shared_task(name="app.tasks.worker.process_zip_upload")
def process_zip_upload(
    physical_file_id: int, 
    kb_tier: str, 
    parent_id: Optional[int], 
    security_level: int, 
    owner_id: int, 
    dept_id: Optional[int]
):
    """
    异步处理压缩包: 解压 -> 递归创建逻辑节点 -> 触发切片
    """
    import zipfile
    import shutil
    import tempfile
    from app.models.knowledge import KnowledgePhysicalFile, KbType, KbTier, SecurityLevel

    with SyncSessionLocal() as session:
        phys = session.get(KnowledgePhysicalFile, physical_file_id)
        if not phys:
            return "Physical file not found"
            
        abs_path = os.path.join(settings.STORAGE_ROOT, phys.file_path)
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(abs_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            def process_dir(current_path, current_parent_id):
                for item in os.listdir(current_path):
                    item_path = os.path.join(current_path, item)
                    if os.path.isdir(item_path):
                        # 创建目录节点
                        dir_node = KnowledgeBaseHierarchy(
                            kb_name=item,
                            kb_type=KbType.DIRECTORY,
                            kb_tier=KbTier(kb_tier),
                            security_level=SecurityLevel(security_level),
                            parent_id=current_parent_id,
                            owner_id=owner_id,
                            dept_id=dept_id
                        )
                        session.add(dir_node)
                        session.commit()
                        process_dir(item_path, dir_node.kb_id)
                    else:
                        # 创建文件节点并保存物理文件 (简单处理: 压缩包内文件也视为新物理文件)
                        with open(item_path, "rb") as f:
                            content = f.read()
                        
                        from app.core.file_utils import calculate_hash, get_storage_path
                        content_hash = calculate_hash(content)
                        
                        # 检查去重
                        stmt = select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == content_hash)
                        p_exists = session.execute(stmt).scalar_one_or_none()
                        
                        if not p_exists:
                            rel_path = get_storage_path(content_hash, item)
                            f_abs_path = os.path.join(settings.STORAGE_ROOT, rel_path)
                            os.makedirs(os.path.dirname(f_abs_path), exist_ok=True)
                            with open(f_abs_path, "wb") as f_out:
                                f_abs_path_out = f_out.write(content)
                            p_exists = KnowledgePhysicalFile(
                                file_path=rel_path,
                                content_hash=content_hash,
                                file_size=len(content),
                                mime_type="application/octet-stream"
                            )
                            session.add(p_exists)
                            session.commit()
                            
                        file_node = KnowledgeBaseHierarchy(
                            kb_name=item,
                            kb_type=KbType.FILE,
                            kb_tier=KbTier(kb_tier),
                            security_level=SecurityLevel(security_level),
                            parent_id=current_parent_id,
                            physical_file_id=p_exists.file_id,
                            owner_id=owner_id,
                            dept_id=dept_id
                        )
                        session.add(file_node)
                        session.commit()
                        # 触发解析
                        parse_knowledge.delay(file_node.kb_id)

            process_dir(temp_dir, parent_id)
            return "Zip processed successfully"
        except Exception as e:
            return f"Zip processing failed: {str(e)}"
        finally:
            shutil.rmtree(temp_dir)

@shared_task(name="app.tasks.worker.cleanup_gin_index")
def cleanup_gin_index():
    """
    PG 索引清理
    """
    with SyncSessionLocal() as session:
        sql = text("""
            UPDATE knowledge_chunks 
            SET content = '' 
            WHERE chunk_id IN (
                SELECT chunk_id FROM knowledge_chunks 
                WHERE is_deleted = TRUE AND content != '' 
                LIMIT :batch_size 
                FOR UPDATE SKIP LOCKED
            )
        """)
        result = session.execute(sql, {"batch_size": settings.GIN_CLEANUP_BATCH_SIZE})
        session.commit()
        return f"Cleaned {result.rowcount} deleted chunks"

@shared_task(name="app.tasks.worker.db_snapshot")
def db_snapshot():
    """
    执行数据库全量备份 (pg_dump)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"
    archive_dir = os.path.join(settings.STORAGE_ROOT, "archives")
    os.makedirs(archive_dir, exist_ok=True)
    filepath = os.path.join(archive_dir, filename)
    
    env = os.environ.copy()
    env["PGPASSWORD"] = settings.POSTGRES_PASSWORD
    
    cmd = [
        "pg_dump",
        "-h", settings.POSTGRES_HOST,
        "-p", str(settings.POSTGRES_PORT),
        "-U", settings.POSTGRES_USER,
        "-d", settings.POSTGRES_DB,
        "-f", filepath
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
        return f"Database snapshot created: {filepath}"
    except Exception as e:
        return f"Database snapshot failed: {str(e)}"

@shared_task(name="app.tasks.worker.db_restore")
def db_restore(filepath: str):
    """
    从快照恢复数据库 (psql)
    """
    if not os.path.exists(filepath):
        return f"Restore failed: File {filepath} not found"
        
    env = os.environ.copy()
    env["PGPASSWORD"] = settings.POSTGRES_PASSWORD
    
    cmd = [
        "psql",
        "-h", settings.POSTGRES_HOST,
        "-p", str(settings.POSTGRES_PORT),
        "-U", settings.POSTGRES_USER,
        "-d", settings.POSTGRES_DB,
        "-f", filepath
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
        return f"Database restored from: {filepath}"
    except Exception as e:
        return f"Database restore failed: {str(e)}"
