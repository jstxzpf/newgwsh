# 知识库、审批与 AI 问答路由 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。

**目标：** 实现知识资产管理的层次化 CRUD 与替换上传机制，实现公文的审批流程（附带简单的 SIP 签名占位符），以及搭建 HRAG 智能流式问答网关。

**技术栈：** FastAPI, SQLAlchemy, HMAC-SHA256 (用于 SIP), SSE Streaming

---

### 任务 1：知识库管理 (`kb`)

**文件：**
- 创建：`backend/app/schemas/kb.py`
- 创建：`backend/app/api/v1/kb_admin.py`

- [ ] **步骤 1：定义 KB Schemas**

```python
# backend/app/schemas/kb.py
from pydantic import BaseModel
from typing import Optional
from app.models.enums import KBTier, DataSecurityLevel

class KBUploadRequest(BaseModel):
    parent_id: Optional[int] = None
    kb_tier: KBTier = KBTier.PERSONAL
    security_level: DataSecurityLevel = DataSecurityLevel.GENERAL
    # 注意：实际文件上传需要使用 Form 和 UploadFile，这里仅定义依赖参数。
```

- [ ] **步骤 2：编写 KB 路由端点**

```python
# backend/app/api/v1/kb_admin.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgePhysicalFile
from app.models.enums import KBTier, DataSecurityLevel
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import hashlib
import os

router = APIRouter()

@router.get("/hierarchy")
async def get_hierarchy(tier: KBTier = KBTier.PERSONAL, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.is_deleted == False)
    if tier == KBTier.PERSONAL:
        query = query.where(KnowledgeBaseHierarchy.owner_id == current_user.user_id)
    elif tier == KBTier.DEPT:
        query = query.where(KnowledgeBaseHierarchy.dept_id == current_user.dept_id)
    
    result = await db.execute(query)
    items = result.scalars().all()
    # 在实际中这里应该构造嵌套树，暂返回扁平列表供演示
    return {"code": 200, "message": "success", "data": [item.kb_name for item in items]}

@router.get("/snapshot-version")
async def get_snapshot_version(current_user: SystemUser = Depends(get_current_user)):
    import time
    return {"code": 200, "message": "success", "data": {"snapshot_version": int(time.time())}}

@router.post("/upload")
async def upload_file(
    parent_id: int | None = Form(None),
    kb_tier: KBTier = Form(KBTier.PERSONAL),
    security_level: DataSecurityLevel = Form(DataSecurityLevel.GENERAL),
    file: UploadFile = File(...),
    current_user: SystemUser = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 检查物理去重
    result = await db.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == file_hash))
    phys_file = result.scalars().first()
    
    if not phys_file:
        # 这里应该写文件到磁盘，为了简化暂只记录数据库
        phys_file = KnowledgePhysicalFile(content_hash=file_hash, file_path=f"/fake/path/{file.filename}", file_size=len(content))
        db.add(phys_file)
        await db.flush()
        
    kb_node = KnowledgeBaseHierarchy(
        parent_id=parent_id,
        kb_name=file.filename,
        kb_type="FILE",
        kb_tier=kb_tier,
        dept_id=current_user.dept_id,
        security_level=security_level,
        parse_status="UPLOADED" if not phys_file.file_size else "READY", # 简化
        physical_file_id=phys_file.file_id,
        owner_id=current_user.user_id
    )
    db.add(kb_node)
    await db.commit()
    
    return {"code": 200, "message": "success", "data": {"kb_id": kb_node.kb_id}}
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/schemas/kb.py backend/app/api/v1/kb_admin.py
git commit -m "feat: 实现知识库层级与上传 API 骨架"
```

### 任务 2：公文审批与 SIP 存证机制 (`approval`)

**文件：**
- 创建：`backend/app/schemas/approval.py`
- 创建：`backend/app/api/v1/approval.py`
- 创建：`backend/app/core/sip.py`

- [ ] **步骤 1：编写 SIP 归一化核心**

```python
# backend/app/core/sip.py
import unicodedata
import re
import hmac
import hashlib
from app.core.config import settings

def normalize_for_sip(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('|', '\\|')
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def generate_sip_hash(content: str, reviewer_id: int, reviewed_at_iso: str) -> str:
    normalized = normalize_for_sip(content)
    raw_str = f"{normalized}|{reviewer_id}|{reviewed_at_iso}"
    return hmac.new(settings.SIP_SECRET_KEY.encode(), raw_str.encode(), hashlib.sha256).hexdigest()
```

- [ ] **步骤 2：定义 Approval Schemas**

```python
# backend/app/schemas/approval.py
from pydantic import BaseModel
from typing import Optional

class ApprovalReviewRequest(BaseModel):
    action: str # APPROVE or REJECT
    comments: Optional[str] = None
```

- [ ] **步骤 3：编写 Approval 路由逻辑**

```python
# backend/app/api/v1/approval.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.models.system import DocumentApprovalLog, NBSWorkflowAudit
from app.schemas.approval import ApprovalReviewRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.sip import generate_sip_hash
from datetime import datetime, timezone

router = APIRouter()

@router.post("/{doc_id}/review")
async def review_document(doc_id: str, req: ApprovalReviewRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 权限应限定为科室负责人，为简化暂略
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    if doc.status != "SUBMITTED":
        raise BusinessException(409, "公文当前不在待审批状态")
        
    now = datetime.now(timezone.utc)
    
    if req.action == "APPROVE":
        doc.status = "APPROVED"
        sip = generate_sip_hash(doc.content or "", current_user.user_id, now.isoformat())
        log = DocumentApprovalLog(
            doc_id=doc_id, submitter_id=doc.creator_id, reviewer_id=current_user.user_id,
            decision_status="APPROVED", sip_hash=sip, reviewed_at=now
        )
    elif req.action == "REJECT":
        if not req.comments:
            raise BusinessException(400, "驳回必须提供理由")
        doc.status = "REJECTED"
        log = DocumentApprovalLog(
            doc_id=doc_id, submitter_id=doc.creator_id, reviewer_id=current_user.user_id,
            decision_status="REJECTED", rejection_reason=req.comments, reviewed_at=now
        )
    else:
        raise BusinessException(400, "无效的审批动作")
        
    doc.reviewer_id = current_user.user_id
    db.add(log)
    await db.flush()
    
    audit = NBSWorkflowAudit(
        doc_id=doc_id, workflow_node_id=40 if req.action == "APPROVE" else 41,
        operator_id=current_user.user_id, reference_id=log.log_id,
        action_details={"reason": req.comments} if req.comments else {}
    )
    db.add(audit)
    await db.commit()
    
    return {"code": 200, "message": "success", "data": None}
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/core/sip.py backend/app/schemas/approval.py backend/app/api/v1/approval.py
git commit -m "feat: 实现审批流转与底层 SIP 防篡改存证"
```

### 任务 3：HRAG 智能问答流式网关 (`chat`)

**文件：**
- 创建：`backend/app/schemas/chat.py`
- 创建：`backend/app/api/v1/chat.py`

- [ ] **步骤 1：定义 Chat Schemas**

```python
# backend/app/schemas/chat.py
from pydantic import BaseModel
from typing import List

class ChatStreamRequest(BaseModel):
    query: str
    context_kb_ids: List[int] = []
    session_id: str
```

- [ ] **步骤 2：编写 Chat 路由流式输出**

```python
# backend/app/api/v1/chat.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatStreamRequest
from app.models.user import SystemUser
from app.api.dependencies import get_current_user
import asyncio

router = APIRouter()

@router.post("/stream")
async def chat_stream(req: ChatStreamRequest, current_user: SystemUser = Depends(get_current_user)):
    # 模拟 HNSW + BM25 的 RAG 召回与流式回答
    async def fake_ollama_stream():
        yield "data: {\"content\": \"根据挂载的统计台账，\"}\n\n"
        await asyncio.sleep(0.5)
        yield "data: {\"content\": \"2024年一季度总产值为...\"}\n\n"
        await asyncio.sleep(0.5)
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(fake_ollama_stream(), media_type="text/event-stream")
```

- [ ] **步骤 3：挂载主路由**

修改 `backend/app/main.py`：
```python
# backend/app/main.py (追加)
from app.api.v1 import kb_admin, approval, chat
app.include_router(kb_admin.router, prefix="/api/v1/kb", tags=["知识库"])
app.include_router(approval.router, prefix="/api/v1/approval", tags=["审批签批"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["智能问答"])
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/schemas/chat.py backend/app/api/v1/chat.py backend/app/main.py
git commit -m "feat: 实现知识库、审批与问答核心路由挂载"
```