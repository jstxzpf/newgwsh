# 后端逻辑解耦与 Service 层引入 重构计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。

**目标：** 将堆积在 API 路由层（Controller）中的核心业务逻辑下沉至 Service 层，实现职责单一化，并对硬编码常量进行全面清理。

**架构：**
1. 引入 `app/services/` 目录。
2. Service 层负责数据库事务、状态机逻辑、哈希算法等业务规则。
3. API 路由层仅负责请求解析与 Service 调用。

---

### 任务 1：业务常量化与枚举补全

**文件：**
- 修改：`backend/app/models/enums.py`

- [ ] **步骤 1：补全工作流节点 ID 枚举**

```python
# backend/app/models/enums.py (追加)
class WorkflowNodeId(int, enum.Enum):
    DRAFTING = 10
    SNAPSHOT = 11
    SNAPSHOT_RESTORE = 12
    POLISH_REQUESTED = 20
    POLISH_APPLIED = 21
    SUBMITTED = 30
    APPROVED = 40
    REJECTED = 41
    REVISION = 42
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/models/enums.py
git commit -m "refactor: 补全业务工作流节点枚举 (任务 1)"
```

### 任务 2：实现 AuthService 与会话管理解耦

**文件：**
- 创建：`backend/app/services/auth_service.py`
- 修改：`backend/app/api/v1/auth.py`

- [ ] **步骤 1：编写 AuthService**

```python
# backend/app/services/auth_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.models.user import UserSession
import uuid
from datetime import datetime, timedelta, timezone

class AuthService:
    @staticmethod
    async def clear_user_sessions(db: AsyncSession, user_id: int):
        await db.execute(delete(UserSession).where(UserSession.user_id == user_id))

    @staticmethod
    async def create_session(db: AsyncSession, user_id: int, refresh_token_hash: str) -> str:
        session_id = str(uuid.uuid4())
        new_session = UserSession(
            session_id=session_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.add(new_session)
        return session_id
```

- [ ] **步骤 2：重构 Auth 路由**

```python
# backend/app/api/v1/auth.py (调用 AuthService)
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/services/auth_service.py backend/app/api/v1/auth.py
git commit -m "refactor: 引入 AuthService 并解耦登录会话管理 (任务 2)"
```

### 任务 3：实现 DocumentService 与公文流转解耦

**文件：**
- 创建：`backend/app/services/document_service.py`
- 修改：`backend/app/api/v1/documents.py`
- 修改：`backend/app/api/v1/approval.py`

- [ ] **步骤 1：编写 DocumentService 核心逻辑**

包含 `init_document`、`auto_save_draft`（含 DIFF 矩阵）、`process_approval`（含 SIP 生成与审计）。

- [ ] **步骤 2：重构公文与审批路由**

- [ ] **步骤 3：Commit**

```bash
git add backend/app/services/document_service.py backend/app/api/v1/
git commit -m "refactor: 引入 DocumentService 并实现公文/审批逻辑下沉 (任务 3)"
```

### 任务 4：实现 KnowledgeService 与知识库解耦

**文件：**
- 创建：`backend/app/services/knowledge_service.py`
- 修改：`backend/app/api/v1/kb_admin.py`

- [ ] **步骤 1：编写 KnowledgeService**

处理物理哈希碰撞检测、逻辑节点创建等。

- [ ] **步骤 2：重构知识库路由**

- [ ] **步骤 3：Commit**

```bash
git add backend/app/services/knowledge_service.py backend/app/api/v1/kb_admin.py
git commit -m "refactor: 引入 KnowledgeService 解耦文件上传逻辑 (任务 4)"
```