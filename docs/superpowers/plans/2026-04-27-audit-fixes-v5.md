# 第五轮审计缺陷专项修复计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标**：修复第五轮审计发现的 P0/P1/P2 级缺陷，包括运行时错误、越权漏洞、原子性竞态及功能缺失。

**架构**：
- **后端**：补全 Pydantic 模型；加固身份校验；实现行级锁；补全用户管理与排版端点；重构知识库树结构。
- **前端**：统一锁管理调用路径。

---

### 阶段一：P0 阻断级缺陷修复 (Critical)

#### 任务 1：补全 Pydantic 模型与 SSE 鉴权
- [ ] **后端**：在 `documents.py` 中定义 `ApplyPolishRequest`。
- [ ] **后端**：在 `sse.py` 的 `/ticket` 端点中增加 `task_owner` 强校验（查库比对 `creator_id`）。

#### 任务 2：加固锁申请与 Revise 原子性
- [ ] **后端**：在 `documents.py` 的 `acquire_document_lock` 增加 `status == DRAFTING` 校验。
- [ ] **后端**：在 `document_service.py` 的 `revise_document` 中使用 `with_for_update()` 行锁。

---

### 阶段二：P1 功能缺口补全 (High)

#### 任务 3：实现用户管理 CRUD
- [ ] **后端**：创建 `backend/app/api/v1/endpoints/users.py`，实现用户增删改查。
- [ ] **后端**：在 `main.py` 中注册用户路由。

#### 任务 4：实现国标排版触发端点
- [ ] **后端**：在 `documents.py` 中实现 `POST /{doc_id}/format`，派发 Celery 任务。

#### 任务 5：重构知识库层级树
- [ ] **后端**：在 `kb_admin.py` 中实现递归树构建逻辑，返回嵌套 JSON。

---

### 阶段三：P2 流程一致性优化 (Medium)

#### 任务 6：锁管理路径统一与前端对齐
- [ ] **后端**：废弃 `documents.py` 中的重复锁端点，统一至 `/locks` 路由。
- [ ] **前端**：更新 `useLockGuard.ts`，将所有锁操作（申请、心跳、释放）统一指向 `/locks` 路径。

#### 任务 7：审计日志补全与脏数据防御
- [ ] **后端**：在 `apply_document_polish` 端点中增加“修改后应用” vs “直接接受”的区分审计。
- [ ] **后端**：增强 `auto_save` 的 `has_explicit_content` 判断，防御 `null` 值绕过。

---

## 验证计划 (Regression)
1. **并发测试**：模拟并发 `revise` 请求，验证行锁是否生效。
2. **鉴权测试**：尝试使用非所有者 Token 获取 SSE Ticket，验证 403。
3. **状态测试**：对 `SUBMITTED` 状态的公文尝试加锁，验证拦截。
4. **功能测试**：调用 `/users` 列表，验证返回结果。
