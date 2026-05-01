# 国家统计局泰兴调查队公文处理系统 V3.0 - API接口契约设计

> 本文档依据《后端设计方案》、《实施约束规则》和《实体模型设计方案》自动生成。作为前后端分离开发的唯一 API 契约基准，规范了 HTTP 方法、路径、权限边界及核心 Request/Response 数据结构。

---

## 全局规范 (Global API Conventions)

1. **基础路径**: 所有业务 API 统一挂载在 `/api/v1` 前缀下。
2. **鉴权机制**: 请求头须携带 `Authorization: Bearer <Access_Token>`。Refresh Token 存放于 HttpOnly Cookie。
3. **数据格式**: 请求与响应统一使用 `application/json`，除了文件上传使用 `multipart/form-data`，文件下载使用 `application/octet-stream` 流式返回。
4. **统一响应结构** (非流式接口):
```json
{
  "code": 200,             // 业务状态码（200 成功，4xx/5xx 对应 HTTP Status）
  "message": "success",    // 提示信息
  "data": { ... }          // 实际业务载荷（列表为数组，单体为对象）
}
```
5. **分页规范** (Query Params): `?page=1&page_size=20`。列表接口的 `data` 统一为：`{"total": 100, "items": [...]}`。
6. **防沉迷/并发控制**: 关键的写入操作须配合分布式锁或状态机前置校验（如 `HTTP 409 Conflict`）。

---

## 1. Auth & 会话管理 (`/api/v1/auth`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/login` | `POST` | 游客 | **单设备登录**。Req: `{"username", "password"}`。<br/>Res: 返回 Access Token，并清除该账号在 Redis 中的旧会话（踢出旧设备）。 |
| `/me` | `GET` | 登录 | **获取当前用户**。Res: `{"user_id", "username", "role_level", "dept_id"}`。 |
| `/refresh` | `POST` | 登录 | **无感续期**。读取 Cookie 中的 Refresh Token 换发新 Token。 |
| `/logout` | `POST` | 登录 | **登出注销**。清除 Redis 当前 Token 凭证及 Cookie。 |

---

## 2. 核心公文流转 (`/api/v1/documents`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/` | `GET` | 登录 | **公文大厅列表**。Query: `status`, `dept_id`。<br/>**权限隔离**：管理员可见全部；科长可见本科室；科员排除他人 `DRAFTING` 状态草稿。 |
| `/init` | `POST` | 登录 | **新建公文**。Req: `{"doc_type_id": 1, "title": "..."}`。后端自动分配 `doc_id` 并置状态为 `DRAFTING`。 |
| `/{doc_id}` | `GET` | 登录 | **获取公文详情**。包含标题、正文、文种、状态及操作人信息。 |
| `/{doc_id}` | `DELETE`| 属主/超管 | **软删除公文**。Req: 空。同步释放挂钩的 Redis 锁，取消后台关联任务。 |
| `/{doc_id}/auto-save` | `POST` | 锁持有者 | **心跳自动保存草稿**。Req: `{"title", "content"}` (SINGLE模式) 或 `{"title", "draft_content"}` (DIFF模式)。必须前置校验锁归属。**DIFF 保护铁律**：DIFF 模式下若 payload 包含 `content` 键则返回 HTTP 400；SINGLE 模式下若包含 `draft_content` 键则返回 HTTP 400。详细矩阵见《后端设计方案》§二.2。 |
| `/{doc_id}/submit` | `POST` | 锁持有者 | **提交审批**。Req: 触发最后一次保存。返回 `{"doc_id": "...", "status": "SUBMITTED", "log_id": 123}`。状态变更为 `SUBMITTED`，释放锁。 |
| `/{doc_id}/revise` | `POST` | 属主 | **驳回后重修**。前置校验 `status == REJECTED`。原子抢占锁并将状态回退为 `DRAFTING`，返回 `{"lock_token": "...", "lock_expires_at": "..."}`。 |
| `/{doc_id}/snapshots` | `GET/POST`| 属主 | **获取/创建手工快照**。 |
| `/{doc_id}/snapshots/{id}/restore` | `POST` | 属主 | **恢复快照**。覆盖当前草稿区。 |
| `/{doc_id}/apply-polish`| `POST` | 锁持有者 | **接受 AI 润色**。Req: `{"final_content"}`。后端自动触发一次快照备份，再覆写正文。 |
| `/{doc_id}/discard-polish`| `POST`| 锁持有者 | **丢弃 AI 润色**。清空推荐区，正文不变。 |
| `/{doc_id}/download` | `GET` | 属主/审批人/超管 | **下载国标排版文件**。StreamingResponse 字节流返回 `.docx` 文件。 |
| `/{doc_id}/verify-sip`| `GET` | 审计权 | **校验 SIP 存证**。后端对当前正文重新执行完整的归一化流水线（NFKC + 换行压缩 + 分隔符转义 + 空白归一），重新计算 HMAC-SHA256 指纹，与 `document_approval_logs` 中当该公文处于 `APPROVED` 终态的记录存储的 `sip_hash` 进行比对，返回一致/不一致结果。 |

---

## 3. 审批与定稿 (`/api/v1/approval`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/{doc_id}/review` | `POST` | 负责人 | **公文审批**。Req: `{"action": "APPROVE|REJECT", "comments": "..."}`。<br/>前置条件：`status == SUBMITTED`。成功后写入 `document_approval_logs`。<br/>通过时：状态转 `APPROVED`，触发 `task_type=FORMAT` 任务并生成 SIP 存证。<br/>驳回时：状态转 `REJECTED`。 |

---

## 4. 全局任务与 SSE 通知 (`/api/v1/tasks` & `/api/v1/sse`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/tasks/polish` | `POST` | 锁持有者 | **触发 AI 润色**。Req: `{"doc_id", "context_kb_ids":[], "context_snapshot_version", "exemplar_id"}`。返回 `task_id`。 |
| `/tasks/format` | `POST` | 属主/管理员 | **手动触发排版或重排**。Req: `{"doc_id"}`。起草人可在 `DRAFTING` 阶段预览排版；审批通过后系统自动派发（内部调用）；排版失败后属主或管理员可手动重排。**必须检查前置状态**：仅允许 `DRAFTING` 或 `APPROVED` 状态的公文触发此任务，其他状态拦截并报错。 |
| `/tasks/{task_id}` | `GET` | 登录 | **查询任务状态（SSE 降级补偿接口）**。当 SSE 隧道断连且无法重建时，前端降级为此接口轮询补偿。Res: `{"task_id", "task_type", "task_status", "progress_pct", "result_summary", "error_message", "created_at", "completed_at"}`。权限：任务发起人或管理员。 |
| `/tasks/{task_id}/retry`| `POST` | 管理员 | **重试死信任务**。限制 `retry_count < 3` 且状态为 `FAILED` 的任务。 |
| `/sse/ticket` | `POST` | 登录 | **申请长连接票据**。Req: `{"task_id"}`。必须前置校验 Redis 中 `task_owner:{task_id}` 是否等于当前请求的 `user_id`。防重放。 |
| `/sse/{task_id}/events` | `GET` | 持票者 | **建立任务监听隧道**。返回 `text/event-stream`。 |
| `/sse/user-events` | `GET` | 持票者 | **建立个人全局监听隧道**。用于接收 `LOCK_RECLAIMED` 等驱逐事件。 |

---

## 5. 高精度悲观锁 (`/api/v1/locks`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/acquire` | `POST` | 登录 | **申请锁**。Req: `{"doc_id"}`。返回 `{ "lock_token", "ttl" }`。冲突时返回 HTTP 423 Locked。 |
| `/heartbeat` | `POST` | 持锁者 | **心跳续租**。Req: `{"doc_id", "lock_token"}`。返回 `{"next_suggested_heartbeat"}`。 |
| `/release` | `POST` | 持锁者 | **释放锁**。Req: `{"doc_id", "lock_token"}`（常规释放）或 `{"doc_id", "lock_token", "content": "..."}`（`beforeunload` 容灾合并释放，后端在释放锁前先执行正文保存，合并为单一原子请求防竞态丢失）。**注意：如果锁因 TTL 已自然过期不存在，接口必须静默返回 200 而非报错，以兼容清理逻辑**。 |
| `/config` | `GET` | 登录 | **获取锁配置参数**。Res: `{"lock_ttl_seconds": 180, "heartbeat_interval_seconds": 90}`。前端据此初始化心跳定时器。 |
| `/{doc_id}` | `DELETE`| 管理员 | **强制斩断锁**。管理员大盘专用，操作强制写入审计日志。 |

---

## 6. 系统中枢设置 - 基础管理 (`/api/v1/users` & `/api/v1/departments` & `/api/v1/doc-types`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/users/*` | `CRUD` | 管理员 | **用户管理**。包含新建、密码重置、及 `PATCH /{id}/toggle-active` (账号停用，导致全系统 403)。 |
| `/departments/*` | `CRUD` | 管理员 | **科室管理**。包含指定 `dept_head_id` 及启停管理。删除前强制进行级联检查。 |
| `/doc-types/*` | `CRUD` | 管理员 | **文种管理**。`layout_rules` JSON 格式校验。软删除（停用）。 |

---

## 7. 系统中枢设置 - 高级基建 (`/api/v1/sys`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/status` | `GET` | 管理员 | **全局探针**。返回 DB/Redis/Celery/AI 引擎连通性，CPU/内存指标。 |
| `/config` | `PUT` | 管理员 | **动态参数**。持久化 `system_config`。如：锁 TTL、Ollama 超时。 |
| `/prompts` | `GET` | 管理员 | **提示词列表**。返回 `app/prompts/` 下的物理文件信息。 |
| `/prompts/{filename}` | `PUT` | 管理员 | **在线编辑提示词**。覆盖文件内容并记录审计。 |
| `/reload-prompts` | `POST` | 管理员 | **热加载提示词**。通知后端实例重新拉取磁盘提示词入内存 Dict。 |
| `/db-snapshots` | `GET` | 管理员 | **快照列表**。返回历史 `pg_dump` 快照文件信息（时间、大小、触发人、状态）。 |
| `/db-snapshot` | `POST` | 管理员 | **手工快照备份**。触发后台 `pg_dump` 异步任务。 |
| `/db-snapshots/{id}/restore`| `POST` | 管理员 | **快照强制恢复**。高危操作！执行 `pg_restore` 覆盖全量数据（需审计与双重确认锁）。 |
| `/cleanup-cache` | `POST` | 管理员 | **临时文件清理**。清理 OS `/tmp` 中无主或过期的残留文件。 |
| `/gin-maintenance` | `POST` | 管理员 | **PG 索引清理**。批量将 `is_deleted=True` 的向量切片 `content` 置空。 |
| `/scan-orphan-files` | `POST` | 管理员 | **扫描孤立物理文件**。查找无逻辑节点引用的 `knowledge_physical_files` 记录并列出，支持批量清理。 |

---


## 8. 知识库管理 (`/api/v1/kb`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/hierarchy` | `GET` | 登录 | **获取知识库目录树**。Query: `tier` (BASE/DEPT/PERSONAL)。返回嵌套树结构，按 `kb_tier` 和用户权限过滤。 |
| `/snapshot-version` | `GET` | 登录 | **获取目录树版本号**。返回 `{"snapshot_version": <timestamp>}`，用于润色请求时防竞态校验。 |
| `/upload` | `POST` | 按层级 | **上传文件/目录**。`multipart/form-data`。Req: `parent_id`, `kb_tier`, `security_level`, 文件列表。支持单文件/多文件/压缩包。返回创建的节点列表及解析状态。 |
| `/{kb_id}` | `GET` | 登录 | **获取节点详情**。返回节点元数据、解析状态、切片统计。 |
| `/{kb_id}` | `PUT` | 属主/管理员 | **替换上传**。上传新版本文件，旧版本切片软删除。 |
| `/{kb_id}` | `DELETE`| 属主/管理员 | **软删除节点**。`DIRECTORY` 类型触发 `WITH RECURSIVE` 级联软删除，切片 `embedding` 置 NULL。 |

---

## 9. HRAG 智能问答 (`/api/v1/chat`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/stream` | `POST` | 登录 | **流式问答**。Req: `{"query", "context_kb_ids": [], "session_id"}`。返回 `text/event-stream`。后端执行 HNSW+BM25 混合检索 → RRF 融合 → CORE 切片静默废弃 → LLM 流式输出。 |

---

## 10. 安全审计与范文库 (`/api/v1/audit` & `/api/v1/exemplars`)

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/audit` | `GET` | `>= 5` | **安全审计大盘查询**。多条件筛选 `nbs_workflow_audit` 日志流。 |
| `/exemplars` | `GET` | 登录 | **范文列表查询**。Query: `doc_type_id`（可选，按文种过滤）, `tier`（可选，按可见层级过滤）。<br/>Res: 返回符合条件的范文列表（`exemplar_id`, `title`, `doc_type_id`, `tier`）。权限：登录用户可见其权限范围内的范文（`BASE` 全员可见，`DEPT` 仅同科室成员可见）。 |
| `/exemplars/upload` | `POST` | 管理员 | **上传范文**。限制 `.docx` MIME类型，上传后触发 AST 提取。不入向量检索，仅供 few-shot。 |
| `/exemplars/{id}/preview` | `GET` | 登录 | **范文纯文本预览**。 |
| `/exemplars/{id}` | `DELETE`| 管理员 | **软删除范文**。删除前检查当前是否有处于 `DRAFTING` 的草稿正在强引用该范文。 |

---

## 11. 消息与通知 (`/api/v1/notifications`)

> 数据持久化表：`user_notifications`。SSE 瞬时事件与本表持久化记录互为补充。

| 接口路径 | HTTP | 权限 | 核心职责与参数 |
|:---|:---:|:---|:---|
| `/` | `GET` | 登录 | **获取通知列表**。Query: `page`, `page_size`, `is_read`。<br/>Res: `{"total": 5, "items": [{"notification_id", "doc_id", "type", "content", "is_read", "created_at"}]}`。 |
| `/unread-count` | `GET` | 登录 | **获取未读通知数**。用于初始化或刷新时铃铛角标回显。<br/>Res: `{"unread_count": 3}`。 |
| `/{id}/read` | `POST` | 登录 | **标记通知已读**。 |
| `/read-all` | `POST` | 登录 | **一键已读全部**。 |

---

## 附录：SSE 事件协议规范 (SSE Event Protocols)

在使用 `GET /api/v1/sse/{task_id}/events` 和 `GET /api/v1/sse/user-events` 时，后端必须遵循 Server-Sent Events 标准格式推送以下定义事件，确保前后端数据契约强制对齐。

| 事件类型 (`event`) | 监听场景 | 载荷结构 (`data` JSON) | 说明 |
|:---|:---|:---|:---|
| `task.progress` | `/sse/{task_id}/events` | `{"task_id": "...", "progress_pct": 45}` | 任务进度更新。 |
| `task.completed` | `/sse/{task_id}/events` | `{"task_id": "...", "doc_id": "...", "result_summary": {}}` | 任务成功完成，前端依据类型（排版/润色）触发下载或开启 DIFF 模式。 |
| `task.failed` | `/sse/{task_id}/events` | `{"task_id": "...", "error_message": "..."}` | 任务失败，携带具体报错堆栈。 |
| `notification.rejected` | `/sse/user-events` | `{"doc_id": "...", "rejection_reason": "..."}` | 审批驳回。前端需弹出 warning 通知框展示 `rejection_reason`。 |
| `notification.approved` | `/sse/user-events` | `{"doc_id": "..."}` | 审批通过。前端需弹出 success 卡片引导用户下载。 |
| `notification.lock_reclaimed` | `/sse/user-events` | `{"doc_id": "...", "reason": "..."}` | 锁被动回收驱逐。前端需弹出 error 模态框展示 `reason`，并降级至只读模式。 |

---
*文档版本：V3.0 API Contract | 最后更新：2026-04 | 状态：[已对齐基准]*
