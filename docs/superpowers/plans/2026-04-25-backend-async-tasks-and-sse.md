# 泰兴市国家统计局公文处理系统 V3.0 - 异步任务与 SSE 通讯实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现基于 Celery 的异步任务编排与基于 SSE (Server-Sent Events) 的实时状态推流隧道。

**架构：** 
- **任务端**：FastAPI 提交任务 -> Celery Worker 执行 -> Redis 存储状态。
- **推送端**：前端申请 Ticket -> 建立 SSE 连接 -> 后端轮询 Redis 并通过 Generator 推送事件。
- **安全**：SSE Ticket 采用“阅后即焚”机制，与 `task_id` 和 `user_id` 强绑定。

**技术栈：** Celery, Redis, FastAPI, SSE.

---

### 任务 1：初始化 Celery 与异步任务持久化逻辑

**文件：**
- 创建：`backend/app/core/celery_app.py`
- 创建：`backend/app/tasks/worker.py`

- [ ] **步骤 1：配置 Celery 实例**

```python
# backend/app/core/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "app.tasks.worker.*": {"queue": "taixing_tasks"}
}
celery_app.conf.update(task_track_started=True)
```

- [ ] **步骤 2：定义基础任务与状态更新逻辑**

```python
# backend/app/tasks/worker.py
import time
import json
from app.core.celery_app import celery_app
from app.core.redis import redis_client
from app.core.database import SyncSessionLocal
from app.models.document import AsyncTask
from app.core.enums import TaskStatus

def update_task_progress(task_id: str, progress: int, status: TaskStatus, result: str = None):
    # 更新 Redis 供 SSE 快速轮询
    redis_client.set(f"task_status:{task_id}", json.dumps({
        "progress": progress,
        "status": status,
        "result": result
    }), ex=3600)
    
    # 同步更新数据库持久化（使用同步会话）
    with SyncSessionLocal() as db:
        db.query(AsyncTask).filter(AsyncTask.task_id == task_id).update({
            "progress_pct": progress,
            "task_status": status,
            "result_summary": result
        })
        db.commit()

@celery_app.task(bind=True)
def dummy_polish_task(self, doc_id: str):
    task_id = self.request.id
    update_task_progress(task_id, 10, TaskStatus.PROCESSING)
    
    # 模拟 AI 推理耗时
    time.sleep(2)
    update_task_progress(task_id, 50, TaskStatus.PROCESSING)
    
    time.sleep(2)
    update_task_progress(task_id, 100, TaskStatus.COMPLETED, result="AI 润色建议内容预览...")
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/core/celery_app.py backend/app/tasks/worker.py
git commit -m "feat(tasks): initialize celery app and worker with progress tracking"
```

---

### 任务 2：实现 SSE Ticket 交换与隧道机制

**文件：**
- 创建：`backend/app/api/v1/endpoints/sse.py`
- 修改：`backend/app/api/v1/api.py`

- [ ] **步骤 1：实现 SSE 票据生成与事件生成器**

```python
# backend/app/api/v1/endpoints/sse.py
import asyncio
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.core.redis import redis_client
import uuid

router = APIRouter()

@router.post("/ticket")
async def create_sse_ticket(task_id: str, user_id: int):
    # TODO: 校验 task_owner:{task_id} == user_id
    ticket = str(uuid.uuid4())
    # 票据 TTL 15 秒，阅后即焚
    await redis_client.set(f"sse_ticket:{ticket}", task_id, ex=15)
    return {"ticket": ticket}

@router.get("/{task_id}/events")
async def sse_events(task_id: str, ticket: str, request: Request):
    # 1. 校验票据
    stored_task_id = await redis_client.get(f"sse_ticket:{ticket}")
    if not stored_task_id or stored_task_id != task_id:
        raise HTTPException(status_code=403, detail="Invalid or expired ticket")
    
    # 2. 阅后即焚
    await redis_client.delete(f"sse_ticket:{ticket}")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            data = await redis_client.get(f"task_status:{task_id}")
            if data:
                yield f"data: {data}\n\n"
                status_obj = json.loads(data)
                if status_obj["status"] in ["COMPLETED", "FAILED"]:
                    break
            
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **步骤 2：注册 SSE 路由**

```python
# backend/app/api/v1/api.py (修改)
from app.api.v1.endpoints import sse
# ...
api_router.include_router(sse.router, prefix="/sse", tags=["sse"])
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/api/v1/endpoints/sse.py backend/app/api/v1/api.py
git commit -m "feat(sse): implement sse ticket-based push tunnel"
```

---

### 任务 3：集成任务触发接口

**文件：**
- 修改：`backend/app/api/v1/endpoints/documents.py`

- [ ] **步骤 1：添加触发润色任务的接口**

```python
# backend/app/api/v1/endpoints/documents.py (添加)
from app.tasks.worker import dummy_polish_task
from app.models.document import AsyncTask
from app.core.enums import TaskType, TaskStatus
import uuid

@router.post("/{doc_id}/polish")
async def trigger_polish(doc_id: str, user_id: int, db: AsyncSession = Depends(get_async_db)):
    # 1. 持久化任务记录
    task_id = str(uuid.uuid4())
    new_task = AsyncTask(
        task_id=task_id,
        task_type=TaskType.POLISH,
        doc_id=doc_id,
        creator_id=user_id,
        task_status=TaskStatus.QUEUED
    )
    db.add(new_task)
    await db.commit()
    
    # 2. 派发 Celery 任务
    dummy_polish_task.apply_async(args=[doc_id], task_id=task_id)
    
    # 3. 初始状态同步 Redis
    await redis_client.set(f"task_status:{task_id}", json.dumps({
        "progress": 0,
        "status": TaskStatus.QUEUED,
        "result": None
    }), ex=3600)
    
    return {"task_id": task_id}
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/api/v1/endpoints/documents.py
git commit -m "feat(api): add endpoint to trigger async polish task"
```

---
