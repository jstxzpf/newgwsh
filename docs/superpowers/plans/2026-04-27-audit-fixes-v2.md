# 第二轮审计缺陷深度修复计划 (15+ 项)

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 补全缺失的核心 API 端点，修复断裂的业务闭环（唤醒修改、登录守卫），并实现审计日志解耦与知识库层级化。

**架构：** 
- **后端**：扩展 `documents.py`, `tasks.py`, `locks.py`, `auth.py`；引入 FastAPI `BackgroundTasks` 处理审计日志；配置 Celery Beat。
- **前端**：增加 `Login.tsx`，重构路由守卫 `ProtectedRoute.tsx`，完善 `Dashboard.tsx` 唤醒逻辑。

---

### 阶段一：阻断级流程修复 (Critical)

#### 任务 1：修复“唤醒修改”死锁流程
- [ ] **后端**：在 `DocumentService.revise_document` 中确保返回 `lock_token`。
- [ ] **前端**：修改 `Dashboard.tsx`，在跳转前异步调用 `revise` 端点，并暂存 `lock_token`。
- [ ] **前端**：修改 `useLockGuard.ts`，使其能从 `sessionStorage` 恢复外部获取的锁凭证。

#### 任务 2：补全公文详情与列表端点
- [ ] **后端**：实现 `GET /documents` 列表接口（支持三层权限：个人、部门、全库）。
- [ ] **后端**：确保 `GET /documents/{doc_id}` 端点功能完整。

---

### 阶段二：安全性与合规性补全 (High)

#### 任务 3：登录页面与路由守卫
- [ ] **前端**：创建 `frontend/src/pages/Login.tsx`。
- [ ] **前端**：实现 `frontend/src/components/Auth/ProtectedRoute.tsx`。
- [ ] **前端**：更新 `App.tsx` 路由表，增加重定向逻辑。

#### 任务 4：审计日志解耦
- [ ] **后端**：在 `app/services/audit_service.py` 中提取日志写入逻辑。
- [ ] **后端**：在所有业务 Endpoint 中改用 `BackgroundTasks` 异步写入 `WorkflowAudit`。

#### 任务 5：锁管理 API 路径对齐
- [ ] **后端**：在 `backend/app/api/v1/endpoints/locks.py` 补全全局锁监控接口。
- [ ] **后端**：将 `/documents/{doc_id}/lock` 等端点通过别名或重定向对齐至 `/api/v1/locks/` 路径（或保持兼容但增加新路径）。

---

### 阶段三：核心功能闭环 (Medium)

#### 任务 6：快照管理系统
- [ ] **后端**：实现 `GET /documents/{doc_id}/snapshots`。
- [ ] **后端**：实现 `POST /documents/{doc_id}/snapshots` (手动创建)。
- [ ] **后端**：实现 `POST /documents/{doc_id}/snapshots/{snapshot_id}/restore`。

#### 任务 7：任务管理系统补全
- [ ] **后端**：实现 `GET /tasks` 列表与 `DELETE /tasks/{task_id}` 取消逻辑。

#### 任务 8：国标排版下载
- [ ] **后端**：实现 `GET /documents/{doc_id}/download` 接口，支持文件下载流。

#### 任务 9：知识库层级化与版本管理
- [ ] **后端**：修改 `kb_admin.py`，增加 `parent_id` 支持。
- [ ] **后端**：实现 `PUT /kb/{kb_id}/replace` 版本替换逻辑。

---

### 阶段四：性能与健壮性 (Low)

#### 任务 10：Celery Beat 周期任务
- [ ] **后端**：在 `app/tasks/worker.py` 中配置 `on_after_configure` 注册周期任务，清理过期物理文件。

#### 11. 任务 11：知识库 Excel 增强解析
- [ ] **后端**：修改 `parse_kb_file_task`，引入 `pandas` 或 `openpyxl` 提取表头并生成描述性元数据。

#### 任务 12：UI 细节修正
- [ ] **前端**：修改 `App.tsx` 中的 Footer 渲染逻辑，仅在 `/workspace` 路径显示字数。

---

## 验证计划 (Red-Green)
1. **流程验证**：从 Dashboard 点击“唤醒修改”，验证是否自动跳转并持有锁。
2. **安全验证**：直接访问 `/workspace/xxx`，验证是否重定向至 `/login`。
3. **一致性验证**：触发操作后，立即查询数据库，验证审计日志是否稍后异步产生。
4. **功能验证**：手动创建快照并成功恢复。
