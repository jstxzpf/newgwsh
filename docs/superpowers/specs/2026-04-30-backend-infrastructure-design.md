# 后端基础架构设计规格说明 (Backend Infrastructure Design Spec)

## 1. 概览
本设计旨在为“国家统计局泰兴调查队公文处理系统 V3.0”搭建稳健的后端骨架。核心目标是实现 API 层的异步高性能处理与 Celery 后台任务的同步稳定性隔离，同时确立公文状态机和审计的硬性约束。

## 2. 容器化编排 (Docker Orchestration)
使用 `docker-compose.yml` 管理全栈服务。

### 2.1 服务定义
- **db**: PostgreSQL 15 + `pgvector` 插件。
- **redis**: Redis 5.0，作为 Celery Broker 和分布式锁存储。
- **api**: FastAPI 应用，异步运行。
- **worker**: Celery 应用，执行重型任务（AI、排版、解析）。

### 2.2 构建规范
- **基础镜像**: `python:3.10-slim`。
- **镜像源**: 针对国内环境，配置 `pip` 使用清华/阿里源，`apt` 使用 Debian 阿里源。
- **最小化部署**: 采用多阶段构建，减少镜像体积。

## 3. 数据库与会话层 (Database & Session Layer)
实现“异步与同步物理隔离”红线。

### 3.1 会话双轨制
- **AsyncSessionLocal**: 基于 `asyncpg`，用于 `app/api/`。
- **SyncSessionLocal**: 基于 `psycopg2`，用于 `app/tasks/worker.py`。
- **隔离性**: `worker.py` 严禁导入 `asyncpg` 相关代码，防止协程冲突。

### 3.2 核心模型约束
- **TimestampMixin**: 所有表包含 `created_at` 和 `updated_at`。
- **软删除**: `is_deleted` 字段支持逻辑删除，RAG 检索时强制过滤。
- **乐观锁**: `Document` 表包含 `version` 字段。

## 4. 业务安全与状态机 (Business Guard & State Machine)

### 4.1 状态机转换
- **枚举**: `DRAFTING`, `SUBMITTED`, `APPROVED`, `REJECTED`。
- **模型校验**: SQLAlchemy `@validates('status')` 钩子强制路径合法性（如 `APPROVED` 不可回退）。

### 4.2 审计与存证
- **nbs_workflow_audit**: Append-Only 模式，记录状态机流转轨迹。
- **SIP 存证**: 签批时计算 HMAC-SHA256 指纹，使用标准化归一化文本。

## 5. 异步任务与 AI 管理 (Async Tasks & AI Management)

### 5.1 Celery 配置
- **显式注册**: `celery_app.py` 中 `include=["app.tasks.worker"]`。
- **结构化日志**: 使用 `structlog` 生成 JSON 格式日志。

### 5.2 提示词热加载
- **存储**: `app/prompts/*.txt`。
- **单例加载**: `PromptLoader` 负责缓存与热重载。
- **占位符**: 使用 `str.format_map` 安全渲染。

## 6. 环境参数 (Environment Variables)
- `POSTGRES_ASYNC_URL`: `postgresql+asyncpg://...`
- `POSTGRES_SYNC_URL`: `postgresql+psycopg2://...`
- `OLLAMA_BASE_URL`: 默认 `http://10.132.60.133:11434`
- `SECRET_KEY`: 用于 JWT 和 SIP 签名。
