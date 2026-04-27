# 第三轮审计缺陷深度修复计划 (安全与一致性专项)

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 解决越权风险（Revise/Me）、修复 Refresh Token 轮换、保证抢锁原子性、实现快照云端恢复闭环，并优化水印与任务推送稳定性。

**架构：** 
- **后端**：重构 `auth.py`, `documents.py` 及其对应的 Service 层；引入统一的 `get_current_user` 依赖；优化 Celery 任务异常回滚。
- **前端**：升级 `useAutoSave.ts`, `useTaskWatcher.ts`, `SnapshotRecoveryDrawer.tsx` 和水印组件。

---

### 阶段一：身份验证与安全基座 (High)

#### 任务 1：完善 Token 轮换与真实鉴权
- [ ] **后端**：在 `backend/app/api/v1/endpoints/auth.py` 中更新 `refresh_token`，确保返回新 Cookie。
- [ ] **后端**：实现真实的 `get_current_user` 依赖注入（校验 JWT 并查库）。
- [ ] **后端**：在 `/me` 端点接入该依赖，移除硬编码。

#### 任务 2：前端安全水印优化
- [ ] **前端**：修改 `AntiLeakWatermark.tsx`，移除秒级时间戳，仅保留日期；设置 `zIndex: 9999`。

---

### 阶段二：公文业务逻辑加固 (Critical)

#### 任务 3：修复 `revise` 接口安全性与原子性
- [ ] **后端**：在 `revise_document` 端点增加 `current_user` 校验（仅限起草人）。
- [ ] **后端**：在 `DocumentService.revise_document` 中将 Redis `SET NX` 移至数据库更新之前，并在 DB 失败时回滚锁。

#### 任务 4：自动保存锁凭证校验与防绕过
- [ ] **前端**：修改 `useAutoSave.ts`，在请求中携带 `lockToken`。
- [ ] **后端**：在 `auto_save_document` 端点校验 `lock_token`；优化 `auto_save` 服务逻辑，严格通过 `payload_keys` 判断是否越权修改正文。

#### 任务 5：提交审批前置校验
- [ ] **后端**：在 `DocumentService.submit_document` 中增加标题（非默认）与正文最小长度（10字）校验。

---

### 阶段三：功能一致性与稳定性 (Medium)

#### 任务 6：云端快照恢复闭环
- [ ] **前端**：修改 `SnapshotRecoveryDrawer.tsx`，在 `handleRestore` 中调用后端 RESTORE API。

#### 任务 7：SSE 稳定性与任务列表排序
- [ ] **前端**：在 `useTaskWatcher.ts` 中实现指数退避重连机制（上限 3 次）。
- [ ] **后端**：确保 `list_tasks` 按照 `created_at` 可靠排序。

#### 任务 8：知识库解析鲁棒性
- [ ] **后端**：在 `kb_admin.py` 中使用 Pydantic 模型过滤关系字段，防止循环引用。
- [ ] **后端**：在 `worker.py` 的解析任务异常分支中，增加对已插入脏切片的清理逻辑。

---

## 验证计划
1. **安全性测试**：使用 A 用户 Token 尝试唤醒 B 用户的驳回公文，预期 403。
2. **原子性测试**：模拟 Redis 抢锁成功但 DB 提交失败，验证锁是否被释放。
3. **闭环测试**：恢复快照后刷新页面，验证内容是否持久化在云端。
4. **性能测试**：断开 SSE 连接，观察前端是否自动尝试恢复监听。
