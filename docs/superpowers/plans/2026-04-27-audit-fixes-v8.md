# 第八轮审计缺陷：逻辑、安全与运行环境专项修复计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标**：消除项目中残存的运行时导入错误，清除硬编码测试状态，接入真实的 AI 向量化能力，并加固越权校验与审计链。

**架构**：
- **后端**：规范化模块导入；统一 DB Session 调用；实现 HTTP 状态码与异常类的精准映射；集成 Ollama Embedding 接口。
- **前端**：修复 AntD 组件缺失导入；重置 Auth Store 初始状态以适配 ProtectedRoute 逻辑。

---

### 阶段一：运行时错误消除 (Critical - P0)

#### 任务 1：补全 Pydantic 与 Enums 导入
- [ ] **后端**：在 `tasks.py` 中导入 `BaseModel`。
- [ ] **后端**：在 `approval.py` 和 `locks.py` 中导入 `DocumentStatus`。

#### 任务 2：规范化 DB 会话与前端提示
- [ ] **后端**：在 `audit_service.py` 中将 `async_session_factory` 更正为 `AsyncSessionLocal`。
- [ ] **前端**：在 `useAutoSave.ts` 中导入 `message`。

---

### 阶段二：安全加固与 IDOR 治理 (High - P1)

#### 任务 3：清除硬编码身份
- [ ] **前端**：修改 `useAuthStore.ts`，将 `userInfo` 初始化为 `null`，确保全站身份验证逻辑闭环。

#### 任务 4：越权校验下沉与审计补全
- [ ] **后端**：在 `documents.py` 的 `submit_document` 端点增加 `creator_id` 强校验。
- [ ] **后端**：在 `documents.py` 的 `delete_document` 端点补全 `BackgroundTasks` 审计日志。

---

### 阶段三：AI 能力增强与异常统一 (Medium - P2)

#### 任务 5：接入真实语义 Embedding
- [ ] **后端**：在 `chat_service.py` 中实现 `get_embedding` 辅助函数（调用 Ollama API）。
- [ ] **后端**：在 `hybrid_search` 中移除伪向量（[0.0...0]），改用真实计算结果。

#### 任务 6：定义业务异常类
- [ ] **后端**：在 `app/core/exceptions.py` 中定义业务专用异常，并重构 Service 层与 Endpoint 层的错误转换逻辑。

---

## 验证计划
1. **启动测试**：重新启动所有后端服务，验证不再出现 `NameError` 或 `ImportError`。
2. **鉴权回归**：清除浏览器缓存后访问 `/dashboard`，验证是否能正确重定向至 `/login`。
3. **AI 检索验证**：提交包含关键词的查询，验证搜索结果是否具备语义相关性（而非随机）。
4. **审计回归**：执行公文删除，在数据库中查询 `nbs_workflow_audit` 验证日志是否已产生。
