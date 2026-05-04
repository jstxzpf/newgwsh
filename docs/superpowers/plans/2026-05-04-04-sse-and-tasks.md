# SSE 通信与异步任务触发 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。

**目标：** 实现基于 `EventSource` 的 Server-Sent Events 单向实时通道，包含“阅后即焚”票据机制（防断连重试死循环），以及对 `POLISH` 和 `FORMAT` 等异步任务的 FastAPI 派发端点。

**架构：** Redis 存储 `task_owner:{task_id}` 和临时 `ticket`。FastAPI 的 `StreamingResponse` 维持连接，并在后台任务（或 Redis Pub/Sub）中推流。

**技术栈：** FastAPI, Redis, Sse-starlette / StreamingResponse, Celery

---

### 任务 1：SSE 阅后即焚票据机制

**文件：**
- 创建：`backend/app/core/sse_utils.py`
- 创建：`backend/app/schemas/sse.py`
- 创建：`backend/app/api/v1/sse.py`

- [ ] **步骤 1：封装 SSE 相关的 Redis 操作**

```python
# backend/app/core/sse_utils.py
import uuid
import json
from app.core.locks import redis_client

async def generate_sse_ticket(task_id: str, user_id: int) -> str:
    ticket = str(uuid.uuid4())
    key = f"ticket:{ticket}"
    value = json.dumps({"task_id": task_id, "user_id": user_id})
    await redis_client.set(key, value, ex=15) # 15 秒存活
    return ticket

async def consume_sse_ticket(ticket: str) -> dict | None:
    key = f"ticket:{ticket}"
    value = await redis_client.get(key)
    if value:
        await redis_client.delete(key) # 阅后即焚
        return json.loads(value)
    return None

async def verify_task_owner(task_id: str, user_id: int) -> bool:
    owner_str = await redis_client.get(f"task_owner:{task_id}")
    return owner_str is not None and int(owner_str) == user_id
```

- [ ] **步骤 2：定义 SSE Schemas**

```python
# backend/app/schemas/sse.py
from pydantic import BaseModel

class TicketRequest(BaseModel):
    task_id: str
```

- [ ] **步骤 3：编写 SSE 路由端点**

```python
# backend/app/api/v1/sse.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from app.models.user import SystemUser
from app.schemas.sse import TicketRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.sse_utils import generate_sse_ticket, consume_sse_ticket, verify_task_owner
import asyncio
from app.core.locks import redis_client

router = APIRouter()

@router.post("/ticket")
async def get_ticket(req: TicketRequest, current_user: SystemUser = Depends(get_current_user)):
    is_owner = await verify_task_owner(req.task_id, current_user.user_id)
    if not is_owner:
        raise BusinessException(403, "无权访问此任务的通知")
    
    ticket = await generate_sse_ticket(req.task_id, current_user.user_id)
    return {"code": 200, "message": "success", "data": {"ticket": ticket}}

@router.get("/{task_id}/events")
async def task_events(request: Request, task_id: str, ticket: str = Query(...)):
    # 验证票据（阅后即焚）
    ticket_data = await consume_sse_ticket(ticket)
    if not ticket_data or ticket_data.get("task_id") != task_id:
        raise BusinessException(403, "无效或已过期的票据，请重新申请")
        
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task_events:{task_id}")
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    data = message['data']
                    yield f"event: task_update\ndata: {data}\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"task_events:{task_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/core/sse_utils.py backend/app/schemas/sse.py backend/app/api/v1/sse.py
git commit -m "feat: 实现 SSE 阅后即焚票据与长连接流道"
```

### 任务 2：异步任务网关 (`/tasks`)

**文件：**
- 创建：`backend/app/schemas/task.py`
- 创建：`backend/app/api/v1/tasks.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：定义 Task Schemas**

```python
# backend/app/schemas/task.py
from pydantic import BaseModel
from typing import List, Optional

class PolishTaskRequest(BaseModel):
    doc_id: str
    context_kb_ids: List[int] = []
    context_snapshot_version: Optional[int] = None
    exemplar_id: Optional[int] = None

class FormatTaskRequest(BaseModel):
    doc_id: str
```

- [ ] **步骤 2：编写 Tasks 路由端点**

```python
# backend/app/api/v1/tasks.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import SystemUser
from app.models.document import Document
from app.models.system import AsyncTask
from app.schemas.task import PolishTaskRequest, FormatTaskRequest
from app.core.exceptions import BusinessException
from app.api.dependencies import get_current_user
from app.core.locks import redis_client
from app.tasks.worker import dummy_polish_task
import uuid

router = APIRouter()

@router.post("/polish")
async def trigger_polish(req: PolishTaskRequest, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 幂等拦截
    result = await db.execute(select(AsyncTask).where(
        AsyncTask.doc_id == req.doc_id, 
        AsyncTask.task_type == "POLISH",
        AsyncTask.task_status.in_(["QUEUED", "PROCESSING"])
    ))
    existing_task = result.scalars().first()
    if existing_task:
        return {"code": 202, "message": "任务已在进行中", "data": {"task_id": existing_task.task_id}}

    doc_result = await db.execute(select(Document).where(Document.doc_id == req.doc_id))
    doc = doc_result.scalars().first()
    if not doc or doc.status != "DRAFTING":
        raise BusinessException(409, "当前状态不可润色")

    task_id = str(uuid.uuid4())
    new_task = AsyncTask(
        task_id=task_id,
        task_type="POLISH",
        doc_id=req.doc_id,
        creator_id=current_user.user_id,
        input_params=req.model_dump()
    )
    db.add(new_task)
    await db.commit()
    
    # 写入 Redis 用于 SSE 权限绑定
    await redis_client.set(f"task_owner:{task_id}", current_user.user_id, ex=86400) # 1天TTL
    
    # 派发 Celery 任务
    dummy_polish_task.delay(task_id, req.doc_id)
    
    return {"code": 202, "message": "accepted", "data": {"task_id": task_id}}

@router.get("/{task_id}")
async def get_task_status(task_id: str, current_user: SystemUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AsyncTask).where(AsyncTask.task_id == task_id))
    task = result.scalars().first()
    if not task:
        raise BusinessException(404, "任务不存在")
    return {"code": 200, "message": "success", "data": {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "task_status": task.task_status,
        "progress_pct": task.progress_pct,
        "result_summary": task.result_summary,
        "error_message": task.error_message
    }}
```

- [ ] **步骤 3：挂载主路由**

```python
# backend/app/main.py (在 include_router 区增加)
from app.api.v1 import sse, tasks
app.include_router(sse.router, prefix="/api/v1/sse", tags=["SSE流"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["异步任务"])
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/schemas/task.py backend/app/api/v1/tasks.py backend/app/main.py
git commit -m "feat: 实现异步任务派发与状态轮询接口"
```