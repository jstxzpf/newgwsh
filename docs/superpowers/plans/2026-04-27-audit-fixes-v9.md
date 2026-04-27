# 第九轮审计缺陷：逻辑与配置深度解耦优化计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标**：全量迁移硬编码参数至配置中心，实现后端 Settings 模型补全与前端 Vite 环境变量注入，确保系统具备“参数外置、热调优、多环境适配”的能力。

**架构**：
- **后端**：扩展 `Settings` 类；重构 `RateLimiter`, `Celery Beat`, `Hybrid Search` 及 `SSE` 模块以接入配置。
- **前端**：构建全局 `config.ts`；重构所有组件与 Hook，移除硬编码常量，实现 `import.meta.env` 驱动。

---

### 阶段一：后端配置中心扩容 (High)

#### 任务 1：Settings 模型补全
- [ ] **后端**：修改 `backend/app/core/config.py`。
    - 补充 AI 引擎、文件存储、重试策略、分页默认值、RAG 阈值、SSE 频率等 10+ 个核心配置项。

#### 任务 2：算力限流与定时任务解耦
- [ ] **后端**：修改 `backend/app/api/dependencies.py`，使 `RateLimiter` 动态读取 `settings` 参数。
- [ ] **后端**：修改 `backend/app/core/celery_app.py`，将清理任务的 Crontab 表达式外置。

#### 任务 3：业务逻辑深度参数化
- [ ] **后端**：修改 `backend/app/services/chat_service.py`。
    - 将 `vector_top_k`, `bm25_top_k`, `rrf_k` 等召回参数接入 `settings`。
- [ ] **后端**：修改 `backend/app/api/v1/endpoints/sse.py`，参数化轮询间隔。
- [ ] **后端**：修改 `backend/app/services/kb_service.py`，使用配置定义的物理存储路径。
- [ ] **后端**：修改 `backend/app/api/v1/endpoints/audit.py`，参数化日志拉取上限。

---

### 阶段二：前端环境变量驱动 (High)

#### 任务 4：全局配置抽象
- [ ] **前端**：创建 `frontend/src/config.ts`，定义 `appConfig` 对象并映射 `import.meta.env`。
- [ ] **前端**：创建 `frontend/.env.example` 模板。

#### 任务 5：引用注入与清理
- [ ] **前端**：重构 `api/client.ts`, `useAutoSave.ts`, `useTaskWatcher.ts`, `App.tsx` 等。
- [ ] **前端**：更新 `AntiLeakWatermark.tsx`, `A4Engine.tsx`, `VirtualDocTree.tsx`, `KnowledgeBase.tsx` 中的常量引用。

---

## 验证计划
1. **配置有效性测试**：在 `.env` 中修改 `AUTO_SAVE_INTERVAL` 为 5 秒，验证前端自动保存频率是否立即改变。
2. **算力限流测试**：将限流阈值降为 1，验证是否能正确触发 429 拦截。
3. **检索调优测试**：调整 `RAG_VECTOR_SIMILARITY_THRESHOLD` 为 0.9，验证低相似度召回是否被成功拦截。
4. **环境适配验证**：验证修改 `UPLOAD_DIR` 后，新上传的知识库文件是否存储在指定的新路径。
