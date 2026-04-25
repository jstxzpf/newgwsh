# 泰兴市国家统计局公文处理系统 V3.0 (newgwsh)

## 项目简介
本系统是为泰兴市国家统计局定制开发的一套集公文起草、AI 语义润色、HRAG 智能问答、国标物理排版及全生命周期审计于一体的智慧政务办公平台。系统通过 A4 拟物化引擎和严格的司法级存证技术，保障了公文处理的规范性与安全性。

## 核心特性
*   **A4 拟物化核心引擎**：严格锁定 794px 国标尺寸，支持动态缩放与单行 28 字物理布局校准。
*   **AI 语义润色与 DIFF 比对**：支持一键触发 AI 润色，并提供左右分屏的建议稿对比修改视图。
*   **HRAG 穿透式智能问答**：基于 `pgvector` 语义召回与 `BM25` 全文检索的混合 RAG 算法，支持知识库上下文挂载。
*   **司法级 SIP 存证**：采用 NFKC 文本归一化与 HMAC-SHA256 技术，实现公文终稿的防篡改指纹存证。
*   **金融级并发冲突保护**：基于 Redis Redlock 的悲观锁机制，支持跨终端休眠唤醒后的自动锁续约。
*   **全生命周期审计**：自动化 WorkflowAudit 流水账记录与云端“后悔药”快照恢复机制。

## 技术栈
*   **前端**：React 19, TypeScript, Vite, Ant Design v6, Zustand (Persist), Axios.
*   **后端**：FastAPI, Celery (Distributed Tasks), SQLAlchemy 2.0 (Async/Sync Isolation).
*   **存储/算力**：PostgreSQL 15 (pgvector), Redis 5.0, Ollama (Gemma LLM).
*   **安全**：JWT (HttpOnly Cookie), SSE Ticket 阅后即焚, IP 子网路由守卫, 令牌桶限流。

## 快速开始

### 1. 环境准备
*   Python 3.10+
*   Node.js 18+
*   PostgreSQL 15 (需安装 pgvector 扩展)
*   Redis 5.0+

### 2. 后端启动
```bash
cd backend
pip install -r requirements.txt
# 配置 .env 文件
uvicorn app.main:app --reload --port 8000
# 启动 Celery Worker
celery -A app.core.celery_app worker --loglevel=info -Q taixing_tasks
```

### 3. 前端启动
```bash
cd frontend
npm install
npm run dev
```

## 项目结构
*   `backend/`：FastAPI 后端核心代码。
*   `frontend/`：React 19 拟物化 UI 交互层。
*   `documents/`：系统原始设计方案与实施准则。
*   `docs/superpowers/plans/`：项目分阶段实现计划书。

## 许可证
仅供泰兴市国家统计局内部使用。
