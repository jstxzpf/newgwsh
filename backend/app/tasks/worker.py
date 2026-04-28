import time
import json
import redis
import os
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.document import AsyncTask, Document
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk, KnowledgePhysicalFile
from app.core.enums import TaskStatus
from app.core.config import settings
from sqlalchemy import text
from openpyxl import load_workbook
from markitdown import MarkItDown
from markdown_it import MarkdownIt
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn

# 1. 建立单例同步 Redis 客户端供 Worker 使用
sync_redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def update_task_progress(task_id: str, progress: int, status: TaskStatus, result: str = None, db_session=None):
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
        if db_session is None: db.close()

@celery_app.task(bind=True, max_retries=settings.MAX_TASK_RETRY_COUNT)
def format_document_task(self, doc_id: str):
    """
    真实国标排版引擎：基于 AST 识别标题层级并设置对应样式 (对齐基准 §IV)
    """
    task_id = self.request.id
    with SyncSessionLocal() as db:
        update_task_progress(task_id, 10, TaskStatus.PROCESSING, db_session=db)
        try:
            doc = db.query(Document).filter(Document.doc_id == doc_id).first()
            if not doc: raise ValueError("Document not found")
            
            docx = DocxDocument()
            
            # 使用 MarkdownIt 解析 AST
            md = MarkdownIt()
            tokens = md.parse(doc.content or "")
            
            # 1. 强制写入公文大标题
            title_p = docx.add_paragraph()
            title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = title_p.add_run(doc.title or "无标题公文")
            run.font.size = Pt(22) # 二号
            run.font.color.rgb = RGBColor(255, 0, 0)
            run.bold = True
            run.font.name = '方正小标宋简体'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '方正小标宋简体')

            # 2. 遍历 AST 渲染正文
            for i, token in enumerate(tokens):
                if token.type == "heading_open":
                    level = int(token.tag[1]) # h1, h2...
                    p = docx.add_paragraph()
                    p.paragraph_format.line_spacing = Pt(28)
                    
                    content_token = tokens[i+1] if i+1 < len(tokens) else None
                    text = content_token.content if content_token and content_token.type == "inline" else ""
                    
                    run = p.add_run(text)
                    if level == 1:
                        run.font.size = Pt(16) # 三号
                        run.bold = True
                        run.font.name = '黑体'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
                    elif level == 2:
                        run.font.size = Pt(16)
                        run.bold = True
                        run.font.name = '楷体_GB2312'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体_GB2312')
                    else:
                        run.font.size = Pt(16)
                        run.font.name = '仿宋_GB2312'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
                        
                elif token.type == "paragraph_open":
                    if i > 0 and tokens[i-1].type == "heading_open": continue
                    
                    content_token = tokens[i+1] if i+1 < len(tokens) else None
                    if not content_token or content_token.type != "inline": continue
                    
                    p = docx.add_paragraph()
                    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
                    p.paragraph_format.line_spacing = Pt(28)
                    p.paragraph_format.first_line_indent = Pt(32)
                    
                    run = p.add_run(content_token.content)
                    run.font.size = Pt(16)
                    run.font.name = '仿宋_GB2312'
                    run._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')

            # 保存产物
            output_filename = f"NBSTX_{doc_id}_{int(time.time())}.docx"
            temp_dir = os.path.join(settings.UPLOAD_DIR, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            output_path = os.path.join(temp_dir, output_filename)
            docx.save(output_path)
            
            doc.word_output_path = output_path
            db.commit()
            
            update_task_progress(task_id, 100, TaskStatus.COMPLETED, result=output_filename, db_session=db)
        except Exception as e:
            db.rollback()
            raise self.retry(exc=e, countdown=10)

@celery_app.task(bind=True, max_retries=settings.MAX_TASK_RETRY_COUNT)
def dummy_polish_task(self, doc_id: str):
    task_id = self.request.id
    with SyncSessionLocal() as db:
        update_task_progress(task_id, 10, TaskStatus.PROCESSING, db_session=db)
        try:
            doc = db.query(Document).filter(Document.doc_id == doc_id).first()
            if not doc: raise ValueError("Document not found")
            
            import httpx
            with httpx.Client(timeout=settings.OLLAMA_REQUEST_TIMEOUT) as client:
                resp = client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": f"你是一个专业的政务公文专家。请润色以下内容，使其更加严谨、符合公文规范：\n\n{doc.content}",
                        "stream": False
                    }
                )
                resp.raise_for_status()
                polished = resp.json().get("response", "").strip()
            
            doc.ai_polished_content = polished
            db.commit()
            update_task_progress(task_id, 100, TaskStatus.COMPLETED, db_session=db)
        except Exception as e:
            db.rollback()
            update_task_progress(task_id, 0, TaskStatus.FAILED, result=str(e), db_session=db)
            raise self.retry(exc=e)

@celery_app.task(bind=True, max_retries=settings.MAX_TASK_RETRY_COUNT)
def parse_kb_file_task(self, kb_id: int, file_path: str):
    """
    知识库文件解析任务：支持 MD AST 切割与 Excel 元数据记录
    """
    task_id = self.request.id
    db = SyncSessionLocal()
    try:
        update_task_progress(task_id, 10, TaskStatus.PROCESSING, db_session=db)
        
        kb_node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
        if not kb_node:
            raise ValueError(f"KnowledgeBase node {kb_id} not found")
            
        ext = os.path.splitext(file_path)[1].lower()
        chunks_to_save = []
        
        if ext in [".md", ".txt", ".docx", ".pdf"]:
            md_text = MarkItDown().convert(file_path).text_content
            md = MarkdownIt()
            tokens = md.parse(md_text)
            
            current_chunk = ""
            current_anchor = "General"
            for token in tokens:
                if token.type == "heading_open":
                    if current_chunk.strip():
                        chunks_to_save.append((current_anchor, current_chunk.strip(), {"type": "markdown_section"}))
                    current_chunk = ""
                elif token.type == "inline" and token.level == 0:
                    if not current_chunk:
                        current_anchor = token.content
                    current_chunk += token.content + "\n"
                elif token.content:
                    current_chunk += token.content + "\n"
            
            if current_chunk.strip():
                chunks_to_save.append((current_anchor, current_chunk.strip(), {"type": "markdown_section"}))
                
        elif ext in [".xlsx", ".xls"]:
            wb = load_workbook(file_path, data_only=True)
            ws = wb.active
            headers = [str(cell.value) if cell.value else f"Col{i}" for i, cell in enumerate(ws[1])]
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
                row_text = " | ".join([f"{headers[i]}: {val}" for i, val in enumerate(row) if val is not None])
                if row_text.strip():
                    meta = {
                        "type": "excel_row",
                        "row_index": row_idx + 2,
                        "sheet_name": ws.title,
                        "headers": headers
                    }
                    chunks_to_save.append((f"Row {row_idx+2}", row_text, meta))

        import httpx
        import structlog
        task_logger = structlog.get_logger()

        for i, (anchor, content, meta) in enumerate(chunks_to_save):
            embedding = None
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                        json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": content}
                    )
                    if resp.status_code == 200:
                        embedding = resp.json().get("embedding")
                    else:
                        task_logger.error("ollama_embedding_failed", 
                                        status_code=resp.status_code, 
                                        response=resp.text,
                                        model=settings.OLLAMA_EMBEDDING_MODEL)
            except Exception as e:
                task_logger.error("ollama_connection_error", error=str(e))

            full_meta = {"anchor": anchor, "task_id": task_id}
            full_meta.update(meta)

            chunk = KnowledgeChunk(
                kb_id=kb_id,
                physical_file_id=kb_node.physical_file_id,
                chunk_index=i,
                content=content,
                embedding=embedding,
                kb_tier=kb_node.kb_tier,
                security_level=kb_node.security_level,
                dept_id=kb_node.dept_id,
                metadata_json=full_meta
            )
            db.add(chunk)
        
        kb_node.parse_status = "READY"
        db.commit()
        update_task_progress(task_id, 100, TaskStatus.COMPLETED, db_session=db)
        
    except Exception as e:
        db.rollback()
        db.execute(text("DELETE FROM knowledge_chunks WHERE kb_id = :kb_id"), {"kb_id": kb_id})
        db.commit()
        
        kb_node = db.query(KnowledgeBaseHierarchy).filter(KnowledgeBaseHierarchy.kb_id == kb_id).first()
        if kb_node:
            kb_node.parse_status = "FAILED"
            db.commit()
            
        update_task_progress(task_id, 0, TaskStatus.FAILED, result=str(e), db_session=db)
        raise self.retry(exc=e)
    finally:
        db.close()

@celery_app.task
def cleanup_expired_files_task():
    """
    定时任务：清理过期临时文件与孤立物理文件 (Batch 3 补完)
    """
    db = SyncSessionLocal()
    try:
        # 1. 清理 temp 目录下的旧文件 (24小时前)
        temp_dir = os.path.join(settings.UPLOAD_DIR, "temp")
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                f_path = os.path.join(temp_dir, f)
                if os.path.getmtime(f_path) < time.time() - 86400:
                    try:
                        os.remove(f_path)
                    except: pass
                    
        # 2. 清理数据库中无引用的物理文件记录
        sql = """
        DELETE FROM knowledge_physical_files 
        WHERE phys_id NOT IN (SELECT physical_file_id FROM knowledge_base_hierarchy WHERE physical_file_id IS NOT NULL)
        """
        db.execute(text(sql))
        db.commit()
    finally:
        db.close()
