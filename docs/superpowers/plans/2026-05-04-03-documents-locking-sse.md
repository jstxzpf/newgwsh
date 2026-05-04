# 公文流转、悲观锁与 SSE 通信 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现核心公文流转（CRUD、自动保存、快照机制）、Redis 分布式悲观锁控制机制，以及基于 EventSource 的 SSE 实时任务与通知推送。

**架构：** 使用 `redis` 实现高精度心跳锁（Redlock），使用 FastAPI 的 `StreamingResponse` 建立 SSE 单向通道，通过 Pydantic schema 对 payload 和锁 token 强校验。

**技术栈：** FastAPI, Redis, SQLAlchemy, Pydantic

---

### 任务 1：高精度分布式悲观锁 (`locks`)

**文件：**
- 创建：`backend/app/core/locks.py` (Redis 锁操作封装)
- 创建：`backend/app/schemas/lock.py`
- 创建：`backend/app/api/v1/locks.py`

- [ ] **步骤 1：封装 Redis 操作库**

```python
# backend/app/core/locks.py
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

async def acquire_redis_lock(doc_id: str, user_id: int, username: str, token: str, ttl: int = 180) -> bool:
    lock_key = f"lock:{doc_id}"
    value = f'{{"user_id": {user_id}, "username": "{username}", "token": "{token}"}}'
    # NX: 只有不存在时才设置，EX: 过期时间
    return await redis_client.set(lock_key, value, nx=True, ex=ttl)

async def release_redis_lock(doc_id: str, user_id: int, token: str) -> bool:
    lock_key = f"lock:{doc_id}"
    import json
    value = await redis_client.get(lock_key)
    if value:
        try:
            data = json.loads(value)
            if data.get("user_id") == user_id and data.get("token") == token:
                await redis_client.delete(lock_key)
                return True
        except:
            pass
    return False

async def extend_redis_lock(doc_id: str, user_id: int, token: str, ttl: int = 180) -> bool:
    lock_key = f"lock:{doc_id}"
    import json
    value = await redis_client.get(lock_key)
    if value:
        try:
            data = json.loads(value)
            if data.get("user_id") == user_id and data.get("token") == token:
                await redis_client.expire(lock_key, ttl)
                return True
        except:
            pass
    return False
```

- [ ] **步骤 2：定义 Lock Pydantic Schemas**

```python
# backend/app/schemas/lock.py
from pydantic import BaseModel
from typing import Optional

class LockAcquireRequest(BaseModel):
    doc_id: str

class LockHeartbeatRequest(BaseModel):
    doc_id: str
    lock_token: str

class LockReleaseRequest(BaseModel):
    doc_id: str
    lock_token: str
    content: Optional[str] = None
```

- [ ] **步骤 3：编写 Locks 路由逻辑**

```python
# backend/app/api/v1/locks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.schemas.lock import LockAcquireRequest, LockHeartbeatRequest, LockReleaseRequest
from app.core.locks import acquire_redis_lock, release_redis_lock, extend_redis_lock
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import uuid

router = APIRouter()

@router.post("/acquire")
async def acquire_lock(req: LockAcquireRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == req.doc_id))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    if doc.status != "DRAFTING":
        raise BusinessException(409, "公文已流转，不可编辑", "READONLY_IMMUTABLE")
    
    token = str(uuid.uuid4())
    success = await acquire_redis_lock(req.doc_id, current_user.user_id, current_user.username, token, ttl=180)
    if not success:
        raise BusinessException(423, "公文正在被他人编辑，当前只读", "READONLY_CONFLICT")
        
    return {"code": 200, "message": "success", "data": {"lock_token": token, "ttl": 180}}

@router.post("/heartbeat")
async def heartbeat_lock(req: LockHeartbeatRequest, current_user: SystemUser = Depends(get_current_user)):
    success = await extend_redis_lock(req.doc_id, current_user.user_id, req.lock_token, ttl=180)
    if not success:
        raise BusinessException(403, "锁已失效或被夺", "LOCK_RECLAIMED")
    return {"code": 200, "message": "success", "data": {"next_suggested_heartbeat": 90, "lock_ttl_remaining": 180}}

@router.post("/release")
async def release_lock(req: LockReleaseRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if req.content is not None:
        # 如果包含 content，执行自动保存合并操作
        result = await db.execute(select(Document).where(Document.doc_id == req.doc_id))
        doc = result.scalars().first()
        if doc and doc.status == "DRAFTING":
            doc.content = req.content
            await db.commit()
            
    await release_redis_lock(req.doc_id, current_user.user_id, req.lock_token)
    return {"code": 200, "message": "success", "data": None}

@router.get("/config")
async def get_lock_config(current_user: SystemUser = Depends(get_current_user)):
    return {"code": 200, "message": "success", "data": {"lock_ttl_seconds": 180, "heartbeat_interval_seconds": 90}}
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/core/locks.py backend/app/schemas/lock.py backend/app/api/v1/locks.py
git commit -m "feat: 实现高精度 Redis 悲观锁申请与心跳机制"
```

### 任务 2：公文 CRUD 与自动保存机制

**文件：**
- 创建：`backend/app/schemas/document.py`
- 创建：`backend/app/api/v1/documents.py`

- [ ] **步骤 1：定义 Document Pydantic Schemas**

```python
# backend/app/schemas/document.py
from pydantic import BaseModel
from typing import Optional

class DocumentInitRequest(BaseModel):
    doc_type_id: int
    title: str

class AutoSaveRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    draft_content: Optional[str] = None
```

- [ ] **步骤 2：编写 Document 路由端点**

```python
# backend/app/api/v1/documents.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.schemas.document import DocumentInitRequest, AutoSaveRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
import uuid

router = APIRouter()

@router.post("/init")
async def init_document(req: DocumentInitRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc_id = str(uuid.uuid4())
    new_doc = Document(
        doc_id=doc_id,
        title=req.title,
        doc_type_id=req.doc_type_id,
        dept_id=current_user.dept_id,
        creator_id=current_user.user_id,
        status="DRAFTING"
    )
    db.add(new_doc)
    await db.commit()
    return {"code": 200, "message": "success", "data": {"doc_id": doc_id}}

@router.get("/{doc_id}")
async def get_document(doc_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False))
    doc = result.scalars().first()
    if not doc:
        raise BusinessException(404, "公文不存在")
    return {
        "code": 200, 
        "message": "success", 
        "data": {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "content": doc.content,
            "status": doc.status,
            "doc_type_id": doc.doc_type_id,
            "ai_polished_content": doc.ai_polished_content,
            "draft_suggestion": doc.draft_suggestion
        }
    }

@router.post("/{doc_id}/auto-save")
async def auto_save(doc_id: str, req: AutoSaveRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.doc_id == doc_id))
    doc = result.scalars().first()
    if not doc or doc.is_deleted:
        raise BusinessException(404, "公文不存在")
    if doc.status != "DRAFTING":
        raise BusinessException(409, "当前状态不可保存")
        
    # DIFF 保护逻辑矩阵
    if doc.ai_polished_content:
        # DIFF 模式
        if req.content is not None:
            raise BusinessException(400, "DIFF 模式下禁止覆盖主正文")
        if req.draft_content is not None:
            doc.draft_suggestion = req.draft_content
    else:
        # SINGLE 模式
        if req.draft_content is not None:
            raise BusinessException(400, "SINGLE 模式下无需提交建议草稿")
        if req.content is not None:
            doc.content = req.content
            
    if req.title is not None:
        doc.title = req.title
        
    await db.commit()
    return {"code": 200, "message": "success", "data": None}
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/schemas/document.py backend/app/api/v1/documents.py
git commit -m "feat: 实现公文初始化与带有 DIFF 矩阵保护的自动保存流"
```

### 任务 3：主路由装配与挂载

**文件：**
- 修改：`backend/app/main.py`

- [ ] **步骤 1：将 locks 和 documents 路由挂载至主应用**

```python
# backend/app/main.py (在 app.include_router 后增加)
from app.api.v1 import locks, documents

app.include_router(locks.router, prefix="/api/v1/locks", tags=["分布式锁"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["公文流转"])
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/main.py
git commit -m "feat: 挂载分布式锁与公文路由"
```