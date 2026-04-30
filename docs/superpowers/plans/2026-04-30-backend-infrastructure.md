# 基础设施初始化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 初始化 FastAPI + Celery + PostgreSQL (pgvector) + Redis 的 Docker 运行环境，并完成本地构建验证。

**架构：**
- 多阶段构建 Docker 镜像。
- Docker Compose 编排 API、Worker、DB 和 Redis。
- 配置中国境内加速源。

**技术栈：** Docker, Docker Compose, FastAPI, Celery, PostgreSQL, Redis.

---

### 任务 1：创建依赖与环境变量模板

**文件：**
- 创建：`requirements.txt`
- 创建：`.env.example`

- [ ] **步骤 1：编写 `requirements.txt`**
  包含：fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, psycopg2-binary, celery, redis, pydantic-settings, structlog, python-multipart。

- [ ] **步骤 2：编写 `.env.example`**
  包含必要的环境变量模板。

---

### 任务 2：创建 Dockerfile

**文件：**
- 创建：`Dockerfile`

- [ ] **步骤 1：编写多阶段构建 Dockerfile**
  - 第一阶段：`builder`，配置阿里源和清华源，安装依赖。
  - 第二阶段：`final`，最小化运行环境。

---

### 任务 3：创建 docker-compose.yml

**文件：**
- 创建：`docker-compose.yml`

- [ ] **步骤 1：编写 docker-compose.yml**
  配置 `db`, `redis`, `api`, `worker` 四个服务。

---

### 任务 4：构建验证

**文件：** 无

- [ ] **步骤 1：执行构建命令**
  运行：`docker compose build`
  预期：所有镜像构建成功。
