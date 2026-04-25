# 泰兴市国家统计局公文处理系统 V3.0 - 后端核心与数据库 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 初始化 FastAPI + Celery 后端基础架构，并建立基于 SQLAlchemy 2.0 的数据库映射模型及异步/同步隔离机制。

**架构：** FastAPI 路由网关使用 `asyncpg` 异步数据库会话，Celery Worker 使用 `psycopg2` 同步数据库会话，物理规避事件循环阻塞。数据实体采用 PostgreSQL 15 + pgvector，支持软删除。

**技术栈：** Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic, Celery, Redis, PostgreSQL (asyncpg/psycopg2), Pytest.

---

### 任务 1：初始化项目架构与配置管理

**文件：**
- 创建：`backend/requirements.txt`
- 创建：`backend/app/core/config.py`
- 创建：`backend/tests/test_config.py`

- [ ] **步骤 1：编写核心依赖清单**

```text
# backend/requirements.txt
fastapi>=0.103.0
uvicorn[standard]>=0.23.2
sqlalchemy>=2.0.20
asyncpg>=0.28.0
psycopg2-binary>=2.9.7
alembic>=1.12.0
celery>=5.3.4
redis>=5.0.0
pydantic>=2.4.2
pydantic-settings>=2.0.3
pgvector>=0.2.3
passlib[argon2]>=1.7.4
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.6
pytest>=7.4.0
pytest-asyncio>=0.21.1
httpx>=0.25.0
```

- [ ] **步骤 2：创建系统全局配置类**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "泰兴市国家统计局公文处理系统"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "taixing_nbs"
    
    # 获取异步与同步连接字符串
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    @property
    def SYNC_DATABASE_URI(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 安全与鉴权
    SECRET_KEY: str = "change_this_to_a_secure_random_string"
    SIP_SECRET_KEY: str = "sip_secure_random_string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    ALLOWED_SUBNETS: List[str] = ["10.132.0.0/16", "127.0.0.1"]
    
    # 业务参数
    LOCK_TTL_SECONDS: int = 180
    HEARTBEAT_INTERVAL_SECONDS: int = 90
    RETRY_BACKOFF_BASE_SECONDS: int = 2
    RETRY_BACKOFF_MAX_SECONDS: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
```

- [ ] **步骤 3：编写配置的单元测试**

```python
# backend/tests/test_config.py
from app.core.config import settings

def test_settings_generation():
    assert settings.PROJECT_NAME == "泰兴市国家统计局公文处理系统"
    assert "postgresql+asyncpg" in settings.ASYNC_DATABASE_URI
    assert "postgresql+psycopg2" in settings.SYNC_DATABASE_URI
    assert settings.LOCK_TTL_SECONDS == 180
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest backend/tests/test_config.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add backend/requirements.txt backend/app/core/config.py backend/tests/test_config.py
git commit -m "chore(backend): init core settings and dependencies"
```

---

### 任务 2：实现数据库隔离会话机制

**文件：**
- 创建：`backend/app/core/database.py`
- 创建：`backend/tests/test_database.py`

- [ ] **步骤 1：编写双轨会话引擎代码**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. 异步引擎与会话 (供 FastAPI 路由层使用)
async_engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 2. 同步引擎与会话 (供 Celery Worker 使用，防止事件循环阻塞)
sync_engine = create_engine(settings.SYNC_DATABASE_URI, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# FastAPI 依赖注入
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

# Celery 依赖使用
def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **步骤 2：编写会话生成测试**

```python
# backend/tests/test_database.py
from app.core.database import async_engine, sync_engine

def test_engines_created():
    assert async_engine.url.drivername == "postgresql+asyncpg"
    assert sync_engine.url.drivername == "postgresql+psycopg2"
```

- [ ] **步骤 3：运行测试验证通过**

运行：`pytest backend/tests/test_database.py -v`
预期：PASS

- [ ] **步骤 4：Commit**

```bash
git add backend/app/core/database.py backend/tests/test_database.py
git commit -m "feat(db): implement async and sync database session isolation"
```

---

### 任务 3：实现全局枚举字典 (Enums)

**文件：**
- 创建：`backend/app/core/enums.py`

- [ ] **步骤 1：编写全局枚举字典**

```python
# backend/app/core/enums.py
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

class WorkflowNode(int, enum.Enum):
    DRAFTING = 10
    POLISH = 12
    FINAL_LAYOUT = 22
    SUBMITTED = 30
    APPROVED = 40
    REJECTED = 41
    REVISION = 42

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

- [ ] **步骤 2：Commit**

```bash
git add backend/app/core/enums.py
git commit -m "feat(models): define core business enums"
```

---

### 任务 4：实现核心数据库实体模型 (第一部分：组织、用户与会话)

**文件：**
- 创建：`backend/app/models/user.py`
- 修改：`backend/app/models/__init__.py`

- [ ] **步骤 1：编写 User 和 Department 模型**

```python
# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Department(Base):
    __tablename__ = "departments"
    
    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_name = Column(String(128), unique=True, nullable=False)
    dept_code = Column(String(32), unique=True)
    dept_head_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="department", foreign_keys="[User.dept_id]")


class User(Base):
    __tablename__ = "system_users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True)
    role_level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    department = relationship("Department", back_populates="users", foreign_keys=[dept_id])


class UserSession(Base):
    __tablename__ = "users_sessions"
    
    session_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    device_info = Column(String(255), nullable=True)
    expires_at = Column(DateTime, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
```

- [ ] **步骤 2：创建 init 聚合导出**

```python
# backend/app/models/__init__.py
from app.models.user import User, Department, UserSession
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/models/user.py backend/app/models/__init__.py
git commit -m "feat(models): add department, user and session entity models"
```

---
> 预留：后续将补充 `backend-documents-model.md` 等计划。
