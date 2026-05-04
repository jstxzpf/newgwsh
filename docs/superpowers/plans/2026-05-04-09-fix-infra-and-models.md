# 基础设施与数据模型 修复补丁计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。

**目标：** 修复后端基础设施臃肿问题，升级数据模型至 SQLAlchemy 2.0 现代风格，完善 ORM 关系导航，补全公文状态机校验，并显式定义向量召回高级索引。

**架构：**
1. Dockerfile 改为多阶段构建。
2. 模型采用 `DeclarativeBase` 风格。
3. 实现 `@validates` 状态转换逻辑。
4. 显式声明 PostgreSQL 扩展索引（HNSW）。

---

### 任务 1：Dockerfile 多阶段构建与忽略规则修复

**文件：**
- 修改：`backend/Dockerfile`
- 创建：`.dockerignore`
- 创建：`backend/.dockerignore`

- [ ] **步骤 1：重构 Dockerfile 为多阶段构建**

```dockerfile
# backend/Dockerfile
# 阶段 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阶段 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# 从 builder 复制已安装的 packages
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **步骤 2：添加 .dockerignore 规则**

```text
# .dockerignore
.git
.venv
__pycache__
*.pyc
.env
node_modules
frontend/dist
backend/app/data/outputs/*
```

- [ ] **步骤 3：Commit**

```bash
git add backend/Dockerfile .dockerignore backend/.dockerignore
git commit -m "refactor: 实现 Docker 多阶段构建与排除规则 (任务 1)"
```

### 任务 2：模型层重构 - 升级至 2.0 风格并完善枚举

**文件：**
- 修改：`backend/app/core/database.py`
- 修改：`backend/app/models/enums.py`
- 修改：`backend/app/models/user.py`

- [ ] **步骤 1：升级 Base 定义**

```python
# backend/app/core/database.py
from sqlalchemy.orm import DeclarativeBase
# ... 保持 engine 定义不变 ...
class Base(DeclarativeBase):
    pass
```

- [ ] **步骤 2：完善模型字段类型**

```python
# backend/app/models/knowledge.py (部分)
# 修改 KnowledgeBaseHierarchy.kb_type 为 SQLEnum(KBTypeEnum)
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/core/database.py backend/app/models/
git commit -m "refactor: 升级模型定义为 SQLAlchemy 2.0 DeclarativeBase 风格"
```

### 任务 3：业务逻辑补全 - 状态机与 ORM 关联

**文件：**
- 修改：`backend/app/models/document.py`
- 修改：`backend/app/models/user.py`
- 修改：`backend/app/models/knowledge.py`

- [ ] **步骤 1：实现公文状态机校验逻辑**

```python
# backend/app/models/document.py (部分)
VALID_TRANSITIONS = {
    DocumentStatus.DRAFTING: [DocumentStatus.SUBMITTED],
    DocumentStatus.SUBMITTED: [DocumentStatus.APPROVED, DocumentStatus.REJECTED],
    DocumentStatus.APPROVED: [],
    DocumentStatus.REJECTED: [DocumentStatus.DRAFTING],
}

@validates('status')
def validate_status_transition(self, key, value):
    if self.status and value != self.status:
        if value not in VALID_TRANSITIONS.get(self.status, []):
            raise ValueError(f"Invalid transition from {self.status} to {value}")
    return value
```

- [ ] **步骤 2：添加 Relationship 导航关联**

```python
# backend/app/models/document.py (部分)
creator = relationship("SystemUser", back_populates="documents")
doc_type = relationship("DocumentType")
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/models/
git commit -m "feat: 补全公文状态机校验与 ORM 关联导航"
```

### 任务 4：高级性能补丁 - 显式索引定义

**文件：**
- 修改：`backend/app/models/knowledge.py`

- [ ] **步骤 1：定义 HNSW 向量索引**

```python
# backend/app/models/knowledge.py (在 KnowledgeChunk 类内)
__table_args__ = (
    Index(
        "idx_chunk_embedding_hnsw",
        "embedding",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    ),
)
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/models/knowledge.py
git commit -m "perf: 显式声明 pgvector HNSW 向量索引"
```