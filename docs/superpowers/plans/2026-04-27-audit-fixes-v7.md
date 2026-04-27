# 第七轮审计缺陷：深度对齐与健壮性加固计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标**：彻底修复权限过滤偏差、漫游状态丢失、错误静默吞噬及中文搜索失效等问题，确保系统 100% 对齐全量基准。

**架构**：
- **后端**：修正 `list_documents` 过滤逻辑；加固 `/review` 权限优先级；实现 `RetryRequest` 文件替换逻辑；将全文检索配置升级为 `zhparser`。
- **前端**：在 `Workspace` 入口实现全量状态恢复（含 DIFF 漫游）；全局补全 `message.error` 错误反馈；更新 UI 按钮规范。

---

### 阶段一：P0 阻断级修复 (Critical)

#### 任务 1：修正科员级文档列表权限
- [ ] **后端**：在 `document_service.py` 的 `list_documents` 中使用 `or_` 条件，允许科员查看本人公文 + 本科室其他人的非草稿公文。

#### 任务 2：实现工作区全量状态漫游恢复
- [ ] **前端**：重构 `Workspace.tsx` 的 `useEffect`。
    - 服务端拉取完整 `doc` 对象。
    - 恢复 `content`、`ai_polished_content`。
    - 漫游 DIFF 识别：若 `ai_polished_content` 存在，自动进入 DIFF 模式并尝试恢复 `draft_suggestion`。

---

### 阶段二：P1 高危缺陷加固 (High)

#### 任务 3：权限等级与审批优先级对齐
- [ ] **后端**：将 `locks.py` 的 `/` 列表接口权限提升至 `role_level >= 99`。
- [ ] **后端**：在 `approval.py` 中精准实现 `dept_head_id` 优先的审批判定。

#### 任务 4：根除前端错误吞噬
- [ ] **前端**：遍历 `useLockGuard.ts`, `useAutoSave.ts`, `Workspace.tsx`, `KnowledgeBase.tsx`。
    - 为所有 `catch` 块补全 `message.error`，确保报错对用户透明。

#### 任务 5：完善任务重试逻辑
- [ ] **后端**：在 `tasks.py` 中定义 `RetryRequest` 模型。
- [ ] **后端**：在 `retry_failed_task` 中支持 `file_path` 的动态替换。

---

### 阶段三：P2 语义检索与 UI 规范 (Medium)

#### 任务 6：中文全文检索升级
- [ ] **后端**：修改 `chat_service.py`，将 `to_tsvector` 的配置从 `'simple'` 升级为 `'zhparser'` (或基准要求的中文分词器)。

#### 任务 7：Workspace 按钮颜色校正
- [ ] **前端**：修改 `Workspace.tsx`，将「AI 智能润色」按钮改为“紫金色”渐变规范。

---

## 验证计划 (Alignment Check)
1. **权限验证**：使用科员 A 账号，验证能否看到科员 B 已提交的公文，且看不到其草稿。
2. **漫游验证**：在浏览器 A 触发润色后关闭，在浏览器 B 打开同一公文，验证是否自动进入 DIFF 模式。
3. **报错验证**：断开后端，点击“润色”，验证前端是否弹出红色错误提示。
4. **重试验证**：调用重试接口并提供新路径，验证 Celery 任务是否使用了新路径。
