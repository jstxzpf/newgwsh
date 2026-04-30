# 后端基础设施初始化设计

**目标：** 初始化 FastAPI + Celery + PostgreSQL (pgvector) + Redis 的 Docker 开发环境。

**架构：**
- **API 层：** 使用 FastAPI，通过 Uvicorn 运行。
- **异步任务层：** 使用 Celery 处理耗时任务。
- **持久化层：** PostgreSQL 15 + pgvector 扩展。
- **缓存/消息代理：** Redis 5.0。

**组件详细设计：**

1.  **Dockerfile:**
    - 使用 `python:3.10-slim`。
    - 多阶段构建：`builder` 阶段安装依赖并导出为 wheels，`final` 阶段仅安装必要的运行环境。
    - 镜像源：`pip` 使用清华源，`apt` 使用阿里源。

2.  **Docker Compose:**
    - `db`: 使用 `ankane/pgvector:v0.5.0`。映射 5432 端口。
    - `redis`: 使用 `redis:5.0-alpine`。
    - `api`: 构建自本地 `Dockerfile`，映射 8000 端口。设置环境变量 `DATABASE_URL`, `REDIS_URL`。
    - `worker`: 构建自本地 `Dockerfile`，启动命令为 `celery -A app.tasks.celery_app worker --loglevel=info`。

3.  **数据流：**
    - 客户端请求经由端口 8000 到达 FastAPI。
    - FastAPI 通过 `SQLAlchemy` (asyncio) 与 PostgreSQL 交互。
    - FastAPI 将任务发布到 Redis 队列。
    - Celery Worker 从 Redis 获取任务并执行，必要时更新数据库。

**测试策略：**
- 验证 `docker compose build` 是否成功。
- 后续将添加健康检查接口。
