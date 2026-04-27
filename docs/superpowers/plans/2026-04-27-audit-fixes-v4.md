# 第四轮审计缺陷深度修复计划 (安全加固与 IDOR 治理)

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 彻底根治 IDOR 越权风险（去外部身份参数化）、修复 SQL 注入隐患、完善锁级联释放、防止自动保存脏数据，并清理 LocalStorage 敏感明文。

**架构：** 
- **后端**：全区块接入 `get_current_user` 依赖；重构 `documents.py`, `locks.py`, `kb_admin.py` 的身份验证逻辑；修正 `chat_service.py` 动态 SQL 参数化。
- **前端**：升级 `useEditorStore.ts` 持久化策略；增强 `Workspace.tsx` 的只读保护与清理逻辑。

---

### 阶段一：身份源唯一化与 IDOR 治理 (Critical - P0)

#### 任务 1：全系统接入 `get_current_user` 依赖
- [ ] **后端**：修改 `backend/app/api/v1/endpoints/documents.py`。
    - 移除所有接口中从 `params` 或 `Form` 传入的 `user_id`, `username`, `role_level` 参数。
    - 强制使用 `current_user: User = Depends(get_current_user)` 作为唯一身份源。
- [ ] **后端**：修改 `backend/app/api/v1/endpoints/locks.py`。
    - 对齐 `acquire_lock_aligned` 和 `force_release_lock` 接口身份源，移除 Mock 数据。
- [ ] **后端**：修改 `backend/app/api/v1/endpoints/kb_admin.py`。
    - 对齐 `upload` 和 `replace` 接口身份源。

#### 任务 2：实现水平越权（跨科室）强制隔离
- [ ] **后端**：更新 `get_document_detail` 端点。
    - 增加部门隔离逻辑：非创建者且非本部门且非超级管理员，拒绝访问（403）。
- [ ] **后端**：优化 `list_documents` 端点。
    - 修正科员查询逻辑：允许查看本科室所有非草稿公文 + 本人所有公文。

---

### 阶段二：数据一致性与 SQL 安全 (Critical - P0)

#### 任务 3：修复流式问答 SQL 注入风险
- [ ] **后端**：修改 `backend/app/services/chat_service.py`。
    - 使用 SQLAlchemy 参数化绑定 `fake_embedding`，禁止字符串拼接。
    - 在 `hybrid_search` 逻辑中注入当前用户的科室鉴权过滤。

#### 任务 4：`apply-polish` 锁凭证强校验
- [ ] **后端**：将 `apply_document_polish` 的 `lock_token` 改为必填项。
- [ ] **后端**：实现端点头部的令牌与持有者强一致性验证。

#### 任务 5：自动保存防破坏机制
- [ ] **后端**：在 `auto_save_document` 中增加逻辑：拒绝同时包含 `content` 和 `draft_content` 的 Payload。
- [ ] **前端**：在 `useAutoSave.ts` 中增加发送前保护：若处于非 DIFF 模式，禁止包含 `content` 键。

---

### 阶段三：存储安全与状态清理 (High - P1)

#### 任务 6：敏感公文脱离 LocalStorage 持久化
- [ ] **前端**：修改 `frontend/src/store/useEditorStore.ts`。
    - 在 `persist` 的 `partialize` 中排除 `content` 和 `aiPolishedContent`，仅保留 `currentDocId` 和 `viewMode`。

#### 任务 7：公文状态转换后的级联清理
- [ ] **后端**：在 `delete_document` 中增加逻辑：软删除时立即释放 Redis 编辑锁。
- [ ] **前端**：在 `handleDiscardPolish` 中增加逻辑：调用接口后清理 Store 缓存及本地持久化项。

#### 任务 8：只读模式 Store 保护
- [ ] **前端**：修改 `Workspace.tsx` 的 `textarea`。
    - 在 `onChange` 回调中增加 `!isReadOnly` 判断，防止通过控制台修改 Value 污染 Store。

---

### 阶段四：运维一致性补全 (Medium - P2)

#### 任务 9：锁释放路径统一
- [ ] **前端**：在 `useLockGuard.ts` 的 cleanup 函数中，统一使用对齐后的 `/locks/release` 接口。

#### 任务 10：知识库解析状态熔断
- [ ] **前端**：修改知识库挂载逻辑（`VirtualDocTree`），对 `parse_status !== 'READY'` 的文件执行禁用（Disabled）。

---

## 验证计划 (Security Regression)
1. **IDOR 专项测试**：手动构造带有他人 `user_id` 的请求，验证后端是否依然以 Token 用户为准。
2. **SQL 注入扫描**：在搜索框输入包含单引号的查询，验证是否报错或导致非预期查询。
3. **泄密风险测试**：在工作区编辑内容后关闭浏览器，重新打开检查 LocalStorage，验证 `content` 字段是否为空。
4. **锁级联验证**：删除一个正在被编辑的公文，验证 Redis 中的 `lock:` 键是否立即消失。
