# 第六轮审计缺陷：全准则基准对齐计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 彻底修复基准对齐偏差，补全系统监控、排版端点、批量上传等功能缺口，确保状态机与锁机制的严丝合缝。

**架构：** 
- **后端**：重构 `sys.py` 探活逻辑；在 `models/knowledge.py` 补全字段；在 `approval.py` 接入真实鉴权；优化 `document_service.py` 状态机；实现 `/users` 与 `/format` 缺失端点。
- **前端**：优化 Dashboard 身份传递逻辑，清理 LocalStorage 冗余字段。

---

### 阶段一：P0 阻断级对齐 (Critical - P0)

#### 任务 1：SSE 归属权校验与锁状态网关
- [ ] **后端**：在 `sse.py` 的 `/ticket` 端点中强制校验 `task.creator_id == current_user.user_id`。
- [ ] **后端**：在 `documents.py` 的 `acquire_document_lock` 中增加 `doc.status == DRAFTING` 的网关校验。

#### 任务 2：模型补全与审批鉴权
- [ ] **后端**：在 `models/knowledge.py` 的 `KnowledgeBaseHierarchy` 模型中添加 `updated_at` 字段。
- [ ] **后端**：重构 `approval.py` 的 `review_document` 端点，从 `get_current_user` 提取 `reviewer_id`，并增加“科室负责人”优先级判定逻辑。

---

### 阶段二：P1 功能缺口补全 (High - P1)

#### 任务 3：系统监控与探活闭环
- [ ] **后端**：重构 `sys.py` 的 `get_system_status`。
    - 实现 DB (`SELECT 1`)、Redis (`ping`)、Celery (`inspect.stats`)、Ollama (`httpx.get`) 的真实探活逻辑。

#### 任务 4：补全缺失业务端点
- [ ] **后端**：在 `documents.py` 中实现 `POST /{doc_id}/format` 触发端点。
- [ ] **后端**：在 `kb_admin.py` 中实现 `POST /batch-upload` 占位逻辑。
- [ ] **后端**：实现 `POST /chat/stream` SSE 流式接口。

#### 任务 5：审计日志闭环
- [ ] **后端**：在 `apply_document_polish` 端点中增加异步审计日志。
- [ ] **后端**：将 `locks.py` 中 `force_release_lock` 的同步审计改为 `BackgroundTasks` 异步写入。

---

### 阶段三：状态机与交互优化 (Medium - P2)

#### 任务 6：公文状态机严苛校验
- [ ] **后端**：在 `DocumentService.submit_document` 中加入 `status in [DRAFTING, REJECTED]` 的状态流转硬校验。
- [ ] **后端**：在 `DocumentService.revise_document` 中加入 `FOR UPDATE` 行级锁（防止极端并发下的状态竞争）。

#### 任务 7：前端身份传递去参数化
- [ ] **前端**：修改 `Dashboard.tsx`，移除 `revise` 调用中的 `user_id` 和 `username` query 参数，后端已支持 Token 提取。

---

## 验证计划
1. **监控验证**：调用 `/sys/status`，验证当 Ollama 或 Redis 离线时能否正确返回 `false`。
2. **状态机测试**：手动修改数据库将公文置为 `SUBMITTED`，尝试调用 `lock` 接口，验证是否被 403 拦截。
3. **并发测试**：模拟并发 `revise` 请求，验证行级锁是否有效防止了重复初始化。
4. **模型验证**：执行 `replace_kb_node` 后检查数据库 `updated_at` 是否已自动更新。
