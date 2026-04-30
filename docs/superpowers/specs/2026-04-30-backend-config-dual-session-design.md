# 后端配置管理与会话双轨制设计

**目标：** 实现符合《实施约束规则》的配置管理系统与异步/同步数据库会话双轨制。

**背景：**
- FastAPI 需要非阻塞的异步会话（asyncpg）以保持高性能。
- Celery 任务在同步环境中运行，使用异步会话会导致事件循环冲突，因此必须使用同步会话（psycopg2）。

**详细设计：**

### 1. 配置管理 (`app/core/config.py`)
- **库：** `pydantic-settings`
- **类：** `Settings(BaseSettings)`
- **核心字段：**
  - `APP_NAME`: str = "NewGWSH"
  - `DEBUG`: bool = False
  - `SECRET_KEY`: str (需从环境变量读取)
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`
- **计算属性：**
  - `ASYNC_DATABASE_URL`: `postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}`
  - `SYNC_DATABASE_URL`: `postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}`

### 2. 数据库引擎与会话 (`app/core/database.py`)
- **异步轨 (FastAPI 专用)：**
  - 使用 `sqlalchemy.ext.asyncio.create_async_engine`。
  - `AsyncSessionLocal` 使用 `async_sessionmaker(expire_on_commit=False)`。
- **同步轨 (Celery 专用)：**
  - 使用 `sqlalchemy.create_engine`。
  - `SyncSessionLocal` 使用标准 `sessionmaker()`。
- **基类：** 定义 `Base(DeclarativeBase)` 供所有模型继承。

### 3. 依赖注入 (`app/api/deps.py`)
- 提供 `get_async_db` 异步生成器。
- 确保在 FastAPI 请求结束时自动关闭会话。

### 4. 验证机制 (`app/test_conn.py`)
- 编写单测性质的脚本，分别测试异步和同步引擎。

**成功标准：**
- 异步引擎能在 FastAPI 路由中正常 CRUD。
- 同步引擎能在独立脚本或 Celery Task 中正常 CRUD，不报协程错误。
- `settings.DEBUG=True` 时，SQL 语句能正确打印到控制台。
