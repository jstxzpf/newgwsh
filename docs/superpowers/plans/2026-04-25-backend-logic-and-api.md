# 泰兴市国家统计局公文处理系统 V3.0 - 后端业务逻辑与 API 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现公文的 CRUD、基于 Redis 的悲观锁机制、自动保存逻辑以及基础的 API 路由。

**架构：** 业务逻辑收束于 `app/services/`，通过 `app/api/v1/` 暴露 RESTful 接口。使用 Redis 实现 Redlock 机制。

**技术栈：** FastAPI, SQLAlchemy 2.0 (Async), Redis, Python 3.10+.

---

### 任务 1：实现 Redis 客户端与锁工具类

**文件：**
- 创建：`backend/app/core/redis.py`
- 创建：`backend/app/core/locks.py`

- [ ] **步骤 1：初始化 Redis 异步客户端**

```python
# backend/app/app/core/redis.py
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis():
    return redis_client
```

- [ ] **步骤 2：实现基于 Redis 的悲观锁逻辑 (`LockService`)**

```python
# backend/app/core/locks.py
import uuid
import json
from datetime import datetime
from app.core.redis import redis_client
from app.core.config import settings

class LockService:
    @staticmethod
    async def acquire_lock(doc_id: str, user_id: int, username: str) -> str | None:
        lock_key = f"lock:{doc_id}"
        token = str(uuid.uuid4())
        lock_data = {
            "user_id": user_id,
            "username": username,
            "acquired_at": datetime.now().isoformat(),
            "token": token
        }
        # 使用 NX (Not Exists) 和 EX (Expire) 保证原子性
        success = await redis_client.set(
            lock_key, 
            json.dumps(lock_data), 
            nx=True, 
            ex=settings.LOCK_TTL_SECONDS
        )
        return token if success else None

    @staticmethod
    async def release_lock(doc_id: str, token: str) -> bool:
        lock_key = f"lock:{doc_id}"
        current_lock = await redis_client.get(lock_key)
        if not current_lock:
            return True
        
        data = json.loads(current_lock)
        if data.get("token") == token:
            await redis_client.delete(lock_key)
            return True
        return False

    @staticmethod
    async def heartbeat(doc_id: str, token: str) -> bool:
        lock_key = f"lock:{doc_id}"
        current_lock = await redis_client.get(lock_key)
        if not current_lock:
            return False
        
        data = json.loads(current_lock)
        if data.get("token") == token:
            await redis_client.expire(lock_key, settings.LOCK_TTL_SECONDS)
            return True
        return False
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/core/redis.py backend/app/core/locks.py
git commit -m "feat(core): implement redis client and pessimistic locking service"
```

---

### 任务 2：实现公文核心业务 Service

**文件：**
- 创建：`backend/app/services/document_service.py`

- [ ] **步骤 1：实现公文初始化、自动保存与查询逻辑**

```python
# backend/app/services/document_service.py
import hashlib
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.document import Document
from app.core.enums import DocumentStatus

class DocumentService:
    @staticmethod
    async def get_document(db: AsyncSession, doc_id: str) -> Optional[Document]:
        result = await db.execute(select(Document).where(Document.doc_id == doc_id, Document.is_deleted == False))
        return result.scalars().first()

    @staticmethod
    async def auto_save(
        db: AsyncSession, 
        doc_id: str, 
        content: Optional[str] = None, 
        draft_content: Optional[str] = None
    ):
        doc = await DocumentService.get_document(db, doc_id)
        if not doc:
            return None
        
        # 校验 DIFF 模式保护：若处于润色态，拒绝直接覆写 content
        if doc.ai_polished_content and content is not None:
            raise ValueError("Cannot overwrite main content while in DIFF mode. Use draft_content instead.")

        if draft_content is not None:
            doc.draft_suggestion = draft_content
        elif content is not None:
            # 计算哈希判重
            new_hash = hashlib.sha256(content.encode()).hexdigest()
            # 简单比较（实际可更复杂）
            if content != doc.content:
                doc.content = content
        
        await db.commit()
        return doc
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/services/document_service.py
git commit -m "feat(services): implement core document business logic"
```

---

### 任务 3：开发公文 API 路由 (网关层)

**文件：**
- 创建：`backend/app/api/v1/endpoints/documents.py`
- 修改：`backend/app/api/v1/api.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：编写公文 CRUD 与锁交互接口**

```python
# backend/app/api/v1/endpoints/documents.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.document_service import DocumentService
from app.core.locks import LockService
from pydantic import BaseModel

router = APIRouter()

class AutoSaveRequest(BaseModel):
    content: str = None
    draft_content: str = None

@pydantic_model_override # 伪代码占位，实际需定义 Schema
@router.post("/{doc_id}/auto-save")
async def auto_save_document(
    doc_id: str, 
    payload: AutoSaveRequest, 
    db: AsyncSession = Depends(get_async_db)
):
    try:
        doc = await DocumentService.auto_save(db, doc_id, payload.content, payload.draft_content)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{doc_id}/lock")
async def acquire_document_lock(doc_id: str, user_id: int, username: str):
    # 注意：此处 user_id 应从鉴权 Token 提取，此处为示意
    token = await LockService.acquire_lock(doc_id, user_id, username)
    if not token:
        raise HTTPException(status_code=409, detail="Document is being edited by another user")
    return {"lock_token": token}
```

- [ ] **步骤 2：组装 API 路由树**

```python
# backend/app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import documents

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
```

- [ ] **步骤 3：挂载到 FastAPI 实例**

```python
# backend/app/main.py (修改)
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(title=settings.PROJECT_NAME)
app.include_router(api_router, prefix=settings.API_V1_STR)
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/api/v1/endpoints/documents.py backend/app/api/v1/api.py backend/app/main.py
git commit -m "feat(api): mount document and lock endpoints"
```

---
