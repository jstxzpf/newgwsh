# 后端配置管理与会话双轨制实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现异步（asyncpg）与同步（psycopg2）数据库会话双轨制，确保 FastAPI 与 Celery 各司其职。

**架构：**
- 使用 `pydantic-settings` 统一管理配置。
- 在 `database.py` 中分别创建 `AsyncEngine` 和 `SyncEngine`。
- 通过 FastAPI 依赖注入（Dependency Injection）向下游提供异步会话。

**技术栈：** Python 3.10, FastAPI, SQLAlchemy 2.0, Pydantic V2, asyncpg, psycopg2.

---

### 任务 1：配置管理实现 (`app/core/config.py`)

**文件：**
- 创建：`app/core/config.py`
- 测试：`app/test_config.py` (临时验证)

- [ ] **步骤 1：编写配置验证测试**
```python
from app.core.config import settings

def test_settings_load():
    assert settings.APP_NAME == "NewGWSH"
    assert "postgresql+asyncpg" in settings.ASYNC_DATABASE_URL
    assert "postgresql+psycopg2" in settings.SYNC_DATABASE_URL
    print("Settings validation passed!")

if __name__ == "__main__":
    test_settings_load()
```

- [ ] **步骤 2：运行测试验证失败**
运行：`python app/test_config.py`
预期：ModuleNotFoundError (app.core.config 不存在)

- [ ] **步骤 3：实现 `Settings` 类**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):
    APP_NAME: str = "NewGWSH"
    DEBUG: bool = False
    SECRET_KEY: str = "dev_secret_key_change_me_in_prod"
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "newgwsh"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

- [ ] **步骤 4：运行测试验证通过**
运行：`python app/test_config.py`
预期：打印 "Settings validation passed!"

- [ ] **步骤 5：Commit**
```bash
git add app/core/config.py
git commit -m "feat: implement configuration management with pydantic-settings"
```

---

### 任务 2：数据库双轨制引擎实现 (`app/core/database.py`)

**文件：**
- 创建：`app/core/database.py`

- [ ] **步骤 1：编写最少实现代码**
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# 异步部分 (FastAPI)
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# 同步部分 (Celery)
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG
)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

class Base(DeclarativeBase):
    pass
```

- [ ] **步骤 2：静态检查验证**
运行：`python -c "from app.core.database import AsyncSessionLocal, SyncSessionLocal; print('Engines initialized')"`
预期：输出 "Engines initialized"

- [ ] **步骤 3：Commit**
```bash
git add app/core/database.py
git commit -m "feat: implement dual-track database sessions (async/sync)"
```

---

### 任务 3：API 依赖项实现 (`app/api/deps.py`)

**文件：**
- 创建：`app/api/deps.py`

- [ ] **步骤 1：实现 `get_async_db` 依赖项**
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **步骤 2：Commit**
```bash
git add app/api/deps.py
git commit -m "feat: add get_async_db dependency for FastAPI"
```

---

### 任务 4：端到端连通性验证 (`app/test_conn.py`)

**文件：**
- 创建：`app/test_conn.py`

- [ ] **步骤 1：编写验证脚本**
```python
import asyncio
from sqlalchemy import text
from app.core.database import async_engine, sync_engine

async def test_async_conn():
    print("Testing Async Connection...")
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(f"Async Result: {result.scalar()}")

def test_sync_conn():
    print("Testing Sync Connection...")
    with sync_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Sync Result: {result.scalar()}")

if __name__ == "__main__":
    try:
        test_sync_conn()
    except Exception as e:
        print(f"Sync connection failed (expected if DB not running): {e}")
    
    try:
        asyncio.run(test_async_conn())
    except Exception as e:
        print(f"Async connection failed (expected if DB not running): {e}")
```

- [ ] **步骤 2：在本地环境运行（即使 DB 未启动也能验证语法）**
运行：`python app/test_conn.py`
预期：由于可能没有真实的数据库运行，脚本可能会报错连接失败，但不能报 `ImportError` 或语法错误。

- [ ] **步骤 3：清理并完成**
删除临时测试文件 `app/test_config.py`。
```bash
git add app/test_conn.py
git commit -m "test: add connectivity verification script"
```
