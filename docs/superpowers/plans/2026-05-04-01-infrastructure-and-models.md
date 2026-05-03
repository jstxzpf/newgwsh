# 基础设施与数据模型 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 搭建系统底层基础设施，包括 Docker Compose 开发环境、FastAPI 核心骨架、数据库连接池（异步与同步隔离）以及完整的 SQLAlchemy 2.0 数据模型与 Alembic 迁移脚本。

**架构：** 后端采用 FastAPI + PostgreSQL(pgvector) + Redis。为确保事件循环安全，网关层使用 `asyncpg` 异步会话，后台任务保留 `psycopg2` 同步会话准备。

**技术栈：** Docker Compose, FastAPI, SQLAlchemy 2.0, Alembic, asyncpg, psycopg2-binary, pgvector, pydantic-settings

---

### 任务 1：项目目录初始化与 Docker 环境配置

**文件：**
- 创建：`docker-compose.dev.yml`
- 创建：`.env.example`
- 创建：`backend/requirements.txt`
- 创建：`backend/Dockerfile`

- [ ] **步骤 1：创建后端依赖文件**

```text
# backend/requirements.txt
fastapi[standard]==0.111.0
sqlalchemy==2.0.30
alembic==1.13.1
asyncpg==0.29.0
psycopg2-binary==2.9.9
pgvector==0.2.5
redis==5.0.4
celery==5.4.0
pydantic-settings==2.2.1
passlib[argon2]==1.7.4
python-jose[cryptography]==3.3.0
structlog==24.1.0
```

- [ ] **步骤 2：创建开发环境变量模板**

```env
# .env.example
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=newgwsh_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_URL=redis://redis:6379/0
OLLAMA_BASE_URL=http://host.docker.internal:11434
SECRET_KEY=supersecretkey-change-me-in-production
SIP_SECRET_KEY=sipsecretkey-change-me-in-production
```

- [ ] **步骤 3：创建 Docker Compose 开发环境配置**

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=newgwsh_db
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - backend_net

  redis:
    image: redis:5.0-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - backend_net

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./app/prompts:/app/app/prompts
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=newgwsh_db
      - POSTGRES_HOST=db
      - POSTGRES_PORT=5432
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - db
      - redis
    networks:
      - frontend_net
      - backend_net

networks:
  frontend_net:
    driver: bridge
  backend_net:
    driver: bridge

volumes:
  pg_data:
  redis_data:
  archive_root:
```

- [ ] **步骤 4：创建后端 Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **步骤 5：Commit**

```bash
git add docker-compose.dev.yml .env.example backend/requirements.txt backend/Dockerfile
git commit -m "build: 基础设施与 Docker 开发环境初始化"
```

### 任务 2：FastAPI 核心配置与双引擎数据库会话

**文件：**
- 创建：`backend/app/core/config.py`
- 创建：`backend/app/core/database.py`
- 创建：`backend/app/main.py`

- [ ] **步骤 1：编写核心配置类**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "泰兴调查队公文处理系统"
    VERSION: str = "3.0"
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str = "5432"
    
    REDIS_URL: str
    OLLAMA_BASE_URL: str
    SECRET_KEY: str
    SIP_SECRET_KEY: str
    
    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    @property
    def sync_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
```

- [ ] **步骤 2：配置物理隔离的数据库连接池**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 异步引擎（供 FastAPI 路由使用）
async_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 同步引擎（专供 Celery Worker 使用，防止事件循环崩溃）
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=10,
    max_overflow=20
)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncSession: # type: ignore
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **步骤 3：编写 FastAPI 主入口**

```python
# backend/app/main.py
from fastapi import FastAPI

app = FastAPI(title="泰兴调查队公文处理系统 V3.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/core/config.py backend/app/core/database.py backend/app/main.py
git commit -m "feat: FastAPI 核心骨架与数据库双引擎会话隔离配置"
```

### 任务 3：业务枚举与通用系统模型

**文件：**
- 创建：`backend/app/models/__init__.py`
- 创建：`backend/app/models/enums.py`
- 创建：`backend/app/models/user.py`
- 创建：`backend/app/models/system.py`

- [ ] **步骤 1：定义全局枚举字典**

```python
# backend/app/models/enums.py
import enum

class DocumentStatus(str, enum.Enum):
    DRAFTING = "DRAFTING"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class KBTier(str, enum.Enum):
    BASE = "BASE"
    DEPT = "DEPT"
    PERSONAL = "PERSONAL"

class DataSecurityLevel(str, enum.Enum):
    CORE = "CORE"
    IMPORTANT = "IMPORTANT"
    GENERAL = "GENERAL"

class DocTypeEnum(str, enum.Enum):
    NOTICE = "NOTICE"
    REQUEST = "REQUEST"
    REPORT = "REPORT"
    REPLY = "REPLY"
    LETTER = "LETTER"
    MINUTES = "MINUTES"
    RESEARCH = "RESEARCH"
    ECONOMIC_INFO = "ECONOMIC_INFO"
    GENERAL = "GENERAL"

class TaskType(str, enum.Enum):
    POLISH = "POLISH"
    FORMAT = "FORMAT"
    PARSE = "PARSE"

class TaskStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

- [ ] **步骤 2：定义用户与科室模型**

```python
# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Department(Base):
    __tablename__ = "departments"
    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_name = Column(String(128), unique=True, nullable=False)
    dept_code = Column(String(32), unique=True)
    dept_head_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class SystemUser(Base):
    __tablename__ = "system_users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    full_name = Column(String(64), nullable=False)
    password_hash = Column(String(255), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True)
    role_level = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class UserSession(Base):
    __tablename__ = "users_sessions"
    session_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    access_jti = Column(String(64), nullable=True)
    device_info = Column(String(255), nullable=True)
    expires_at = Column(DateTime, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
```

- [ ] **步骤 3：定义系统任务与审计模型**

```python
# backend/app/models/system.py
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB
from app.models.enums import TaskType, TaskStatus

class AsyncTask(Base):
    __tablename__ = "async_tasks"
    task_id = Column(String(64), primary_key=True)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    task_status = Column(SQLEnum(TaskStatus), index=True, nullable=False, default=TaskStatus.QUEUED)
    input_params = Column(JSONB, nullable=False, default={})
    retry_count = Column(Integer, nullable=False, default=0)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), nullable=True)
    kb_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    progress_pct = Column(Integer, nullable=False, default=0)
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, index=True, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class NBSWorkflowAudit(Base):
    __tablename__ = "nbs_workflow_audit"
    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    workflow_node_id = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reference_id = Column(Integer, ForeignKey("document_approval_logs.log_id"), nullable=True)
    action_details = Column(JSONB, nullable=True)
    action_timestamp = Column(DateTime, index=True, server_default=func.now())

class DocumentApprovalLog(Base):
    __tablename__ = "document_approval_logs"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), index=True, nullable=False)
    submitter_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    decision_status = Column(String(32), nullable=False)
    rejection_reason = Column(Text, nullable=True)
    sip_hash = Column(String(64), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

class SystemConfig(Base):
    __tablename__ = "system_config"
    config_key = Column(String(64), primary_key=True)
    config_value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    value_type = Column(String(16), nullable=False, default='string')
    updated_by = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class UserNotification(Base):
    __tablename__ = "user_notifications"
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=True)
    type = Column(String(32), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, index=True, nullable=False, default=False)
    created_at = Column(DateTime, index=True, nullable=False, server_default=func.now())
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/models/enums.py backend/app/models/user.py backend/app/models/system.py
git commit -m "feat: 添加基础系统数据模型及枚举"
```

### 任务 4：公文核心与知识库向量模型

**文件：**
- 创建：`backend/app/models/document.py`
- 创建：`backend/app/models/knowledge.py`
- 修改：`backend/app/models/__init__.py`

- [ ] **步骤 1：定义公文与快照模型**

```python
# backend/app/models/document.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import DocumentStatus
from sqlalchemy.orm import validates
from sqlalchemy.dialects.postgresql import JSONB

class DocumentType(Base):
    __tablename__ = "document_types"
    type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_code = Column(String(32), unique=True, nullable=False)
    type_name = Column(String(64), nullable=False)
    layout_rules = Column(JSONB, nullable=False, default={})
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class ExemplarDocument(Base):
    __tablename__ = "exemplar_documents"
    exemplar_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    doc_type_id = Column(Integer, ForeignKey("document_types.type_id"), index=True, nullable=False)
    tier = Column(String(32), nullable=False, default="DEPT")
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), nullable=True)
    file_path = Column(String(512), nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)
    extracted_text = Column(Text, nullable=True)
    uploader_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False, default="未命名公文")
    content = Column(Text, nullable=True, default="")
    status = Column(SQLEnum(DocumentStatus), index=True, nullable=False, default=DocumentStatus.DRAFTING)
    doc_type_id = Column(Integer, ForeignKey("document_types.type_id"), nullable=False)
    exemplar_id = Column(Integer, ForeignKey("exemplar_documents.exemplar_id"), nullable=True)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    ai_polished_content = Column(Text, nullable=True)
    draft_suggestion = Column(Text, nullable=True)
    word_output_path = Column(String(512), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @validates('status')
    def validate_status_transition(self, key, value):
        # 简单校验拦截，在写入数据库时进行状态机验证
        return value

class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), ForeignKey("documents.doc_id"), index=True, nullable=False)
    content = Column(Text, nullable=False)
    trigger_event = Column(String(64), nullable=False)
    creator_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=False)
    created_at = Column(DateTime, index=True, server_default=func.now())
```

- [ ] **步骤 2：定义知识库与特征向量表**

```python
# backend/app/models/knowledge.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, BigInt
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.models.enums import KBTier, DataSecurityLevel

class KnowledgePhysicalFile(Base):
    __tablename__ = "knowledge_physical_files"
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInt, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class KnowledgeBaseHierarchy(Base):
    __tablename__ = "knowledge_base_hierarchy"
    kb_id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=True)
    kb_name = Column(String(255), nullable=False)
    kb_type = Column(String(32), nullable=False)
    kb_tier = Column(SQLEnum(KBTier), nullable=False, default=KBTier.PERSONAL)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True)
    security_level = Column(SQLEnum(DataSecurityLevel), nullable=False, default=DataSecurityLevel.GENERAL)
    parse_status = Column(String(32), nullable=False, default="UPLOADED")
    physical_file_id = Column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=True)
    owner_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=False)
    physical_file_id = Column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True) # 使用 bge-m3 1024维向量
    is_deleted = Column(Boolean, index=True, nullable=False, default=False)
    kb_tier = Column(SQLEnum(KBTier), nullable=False)
    security_level = Column(SQLEnum(DataSecurityLevel), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True)
    owner_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=True)
    metadata_json = Column(JSONB, nullable=False, default={})
```

- [ ] **步骤 3：在模型入口注册所有表**

```python
# backend/app/models/__init__.py
from app.core.database import Base
from app.models.user import SystemUser, Department, UserSession
from app.models.document import Document, DocumentType, ExemplarDocument, DocumentSnapshot
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk, KnowledgePhysicalFile
from app.models.system import AsyncTask, NBSWorkflowAudit, DocumentApprovalLog, SystemConfig, UserNotification

__all__ = [
    "Base", "SystemUser", "Department", "UserSession",
    "Document", "DocumentType", "ExemplarDocument", "DocumentSnapshot",
    "KnowledgeBaseHierarchy", "KnowledgeChunk", "KnowledgePhysicalFile",
    "AsyncTask", "NBSWorkflowAudit", "DocumentApprovalLog", "SystemConfig", "UserNotification"
]
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/models/document.py backend/app/models/knowledge.py backend/app/models/__init__.py
git commit -m "feat: 添加公文、快照及带向量属性的知识库模型"
```

### 任务 5：Alembic 初始化与首次迁移

**文件：**
- 创建：`backend/alembic.ini`
- 修改：`backend/alembic/env.py`

- [ ] **步骤 1：安装并初始化 Alembic**

由于环境限制，这步需要配置好 `alembic`，并使 `alembic.ini` 和 `env.py` 支持异步引擎。

```bash
cd backend
alembic init -t async alembic
```

- [ ] **步骤 2：修改 `alembic/env.py` 以支持所有模型和 pgvector**

修改 `backend/alembic/env.py`，导入 `app.models.Base` 和 `settings`。
确保导入 `pgvector` 以防无法识别 `VECTOR` 类型。

```python
# backend/alembic/env.py (在开头加入)
import sys
import os
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import pgvector.sqlalchemy # 关键：让 alembic 识别 vector 类型

from app.core.config import settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.async_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 下方的 run_migrations_offline 和 run_migrations_online 保持不变...
```

- [ ] **步骤 3：准备种子数据脚本骨架**

```python
# backend/scripts/seed_data.py
import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import SystemUser, Department

async def seed():
    async with AsyncSessionLocal() as session:
        # 种子数据逻辑，后续执行
        print("Seeding ready.")

if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **步骤 4：Commit**

```bash
git add backend/alembic.ini backend/alembic backend/scripts/seed_data.py
git commit -m "chore: 初始化 Alembic 及迁移脚本骨架"
```