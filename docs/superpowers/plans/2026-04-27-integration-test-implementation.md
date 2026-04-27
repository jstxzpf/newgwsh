# 集成测试套件实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建一套自动化集成测试套件，验证全链路业务逻辑、SSE 安全隔离及知识库解析回滚。

**架构：** 使用 `pytest` + `pytest-asyncio` 进行异步测试。通过 `subprocess` 在测试前检测并自动唤醒 Docker 中的 PostgreSQL 和 Redis 容器。使用 `httpx.AsyncClient` 模拟真实 HTTP 请求。

**技术栈：** Pytest, pytest-asyncio, httpx, Docker CLI, SQLAlchemy 2.0, Redis-py, Ollama API。

---

### 1. 预定修改/创建的文件结构
- **创建** `backend/tests/scripts/env_prep.py`: 负责 Docker 容器检测、启动及数据库隔离。
- **创建** `backend/tests/conftest.py`: 定义全局 `db`、`redis`、`client` 等 `async` fixtures。
- **创建** `backend/tests/integration/test_full_workflow.py`: 实现 TC-01（起草 -> 润色 -> 审批）。
- **创建** `backend/tests/integration/test_sse_security.py`: 实现 TC-02（SSE Ticket 越权与单次性验证）。
- **创建** `backend/tests/integration/test_kb_parse.py`: 实现 TC-03（KB 解析失败数据回滚验证）。

---

### 任务 1：环境自愈脚本实现 (Self-Healing)

**文件：**
- 创建：`backend/tests/scripts/env_prep.py`

- [ ] **步骤 1：编写脚本检测并启动 Docker 容器**
```python
import subprocess
import time

def ensure_containers_running():
    # 检查并启动容器
    containers = ["postgres", "redis"]
    for c in containers:
        res = subprocess.run(["docker", "ps", "-f", f"name={c}", "--format", "{{.Names}}"], capture_output=True, text=True)
        if c not in res.stdout:
            print(f"Starting container {c}...")
            subprocess.run(["docker", "start", c])
    # 简单的就绪等待
    time.sleep(2)
```

- [ ] **步骤 2：测试脚本执行**
运行：`python -c "from backend.tests.scripts.env_prep import ensure_containers_running; ensure_containers_running()"`
预期：命令行输出 `Starting...`（如果未运行）或无输出，且 `docker ps` 显示容器已运行。

---

### 任务 2：Pytest 基础架构搭建 (Fixtures)

**文件：**
- 创建：`backend/tests/conftest.py`

- [ ] **步骤 1：定义异步数据库与客户端 Fixture**
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.core.database import Base, engine, get_async_db

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    # 使用测试数据库名，需确保 .env 映射正确或在此硬编码覆盖
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

- [ ] **步骤 2：Commit**
```bash
git add backend/tests/conftest.py
git commit -m "test: add integration test fixtures"
```

---

### 任务 3：TC-01 全链路业务流测试

**文件：**
- 创建：`backend/tests/integration/test_full_workflow.py`

- [ ] **步骤 1：编写全链路测试代码**
```python
import pytest

@pytest.mark.asyncio
async def test_draft_to_approval_flow(client):
    # 1. Init
    res = await client.post("/api/v1/documents/init", json={"title": "集成测试公文"})
    doc_id = res.json()["doc_id"]
    
    # 2. Auto-save
    await client.post(f"/api/v1/documents/{doc_id}/auto-save", json={"content": "正文内容"}, params={"lock_token": "mock-token"})
    
    # 3. Submit
    await client.post(f"/api/v1/documents/{doc_id}/submit")
    
    # 4. Check Status
    res = await client.get(f"/api/v1/documents/{doc_id}")
    assert res.json()["status"] == "SUBMITTED"
```

- [ ] **步骤 2：运行测试并观察结果**
运行：`pytest backend/tests/integration/test_full_workflow.py -v`

---

### 任务 4：TC-02 SSE 安全边界测试

**文件：**
- 创建：`backend/tests/integration/test_sse_security.py`

- [ ] **步骤 1：编写越权测试用例**
```python
@pytest.mark.asyncio
async def test_sse_ticket_isolation(client):
    # 用户 A 申请 Ticket
    res = await client.post("/api/v1/sse/ticket", params={"task_id": "task-a"})
    ticket = res.json()["ticket"]
    
    # 模拟用户 B (无 Token 或不同 Token) 尝试使用此 Ticket
    # 此处需模拟 current_user 注入，或直接测试后端逻辑
    res_b = await client.get(f"/api/v1/sse/task-a/events", params={"ticket": ticket})
    assert res_b.status_code in [401, 403]
```

---

### 任务 5：TC-03 知识库回滚测试

**文件：**
- 创建：`backend/tests/integration/test_kb_parse.py`

- [ ] **步骤 1：编写解析失败回滚测试**
```python
@pytest.mark.asyncio
async def test_kb_parse_rollback(client):
    # 触发一个必然失败的任务（如路径不存在）
    # 检查数据库 knowledge_chunks 是否为空
    pass 
```

---

## 自检报告
1. **规格覆盖度**：
   - [x] 环境自愈 (Task 1)
   - [x] 全链路流转 (Task 3)
   - [x] SSE 安全边界 (Task 4)
   - [x] KB 回滚 (Task 5)
2. **占位符扫描**：Task 5 中的 `pass` 需在执行时具体细化为 `assert` 逻辑。
3. **类型一致性**：统一使用 `AsyncClient` 和 `uuid` 字符串。
