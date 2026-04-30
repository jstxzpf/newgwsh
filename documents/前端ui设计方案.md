# 国家统计局泰兴调查队公文处理系统 V3.0 - 前端 UI 与界面架构设计方案

本方案集合了前端的**交互机制**、**底层状态流**以及**页面路由与模块视图**，作为全站前端的整体架构准则与施工图纸。

---

## 一、 系统拓扑与路由结构 (Routing Topology)

前端采用 React Router 进行受限访问控制，划分为以下核心路由结构：

* **`/login`**：登录页（白名单路由，拦截 401 跳转目标）。
* **`/` (App Shell)**：需鉴权的内部工作空间外壳，默认重定向至 `/dashboard`。全局渲染 `AntiLeakWatermark` 水印。
    * **`/dashboard`**：个人工作台（概览、待办事项）。
    * **`/documents`**：公文管理中心（支持按状态、科室维度筛选列表）。
    * **`/workspace/:doc_id`**：沉浸式公文工作区（A4 画板起草与 DIFF 比对引擎）。
    * **`/knowledge`**：统计知识资产库（管理台账、上传与切片状态可视化）。
    * **`/chat`**：HRAG 智能穿透问答中心（带上下文挂载功能的对话板）。
    * **`/tasks`**：异步任务管理中心（全局 AI 推理与排版进度大盘，支持错误任务一键重试）。
    * **`/approvals`**：科长签批管控台（仅“公文所属科室中 `role_level >= 5` 的用户”或“科室负责人 `dept_head_id`”可见，处理同科室提交审核的公文）。
    * **`/settings`**：系统中枢设置台（全局防线参数监控、安全审计溯源、账户及死锁重置等，具备基于角色的阶梯展示）。

---

## 二、 全局视觉与防泄密体系 (Design System & Security)

> **对 AI Agent 的指令**：在配置 Ant Design v6 主题（Theme Token）时，必须严格应用以下 Token 与拦截组件。本系统**不使用 Tailwind CSS**，所有样式通过 Ant Design 主题定制 + 少量自定义 CSS 实现。

### 1. 色彩与排版矩阵 (`TAIXING_TOKENS`)
* **主品牌色**：政务蓝 `#003366`（用于 Header、主要按钮、激活状态）。
* **背景底色**：珍珠白 `#fcfcfc`（用于公文画板），深空灰背景 `#f0f2f5`（用于工作区外层容器，形成物理纸张的高对比度）。
* **字体防御链 (Typography)**：
  * **全局优先**：`font-family: "方正仿宋_GBK", "FZFS", "仿宋_GB2312", "仿宋", "FangSong", "STFangsong", "华文仿宋", "Noto Serif CJK SC", serif;`。必须以此链条保障在政务内网（Windows 及信创环境）下的无缝渲染。针对国产 Linux（如统信 UOS、麒麟 OS）环境，已内置 `FZFS` 及对应开源降级字体，严禁回退至黑体。
  * **非公文区字体**：系统 UI 界面（侧边栏、状态栏）使用 `sans-serif` 或系统默认字体以提升易读性。

### 2. 全局防泄密水印 (`AntiLeakWatermark`)
* 采用覆盖整个 `#root` 的绝对定位蒙层（`pointer-events: none`）。
* 从 `useAuthStore` 及 `/api/v1/auth/me` 返回值中动态提取当前用户的 `username`（作为统一登录工号）、`department_name` 及当前时间组成复合标识，全环节术语统一以此字段作为身份标记防混淆（注意：水印内严禁显示 `client_ip` 以免引发敏感隐私合规问题）。
* 以 `rotate(-20deg)` 斜向平铺，透明度设为极限的 `opacity: 0.08`，实现静默追责与截屏溯源。

---

## 三、 核心页面布局原型定义 (Page Layouts)

### 1. 全局主框架 (App Shell)
* **顶栏导航 (Header)**：高度 `64px`，背景白。左侧展示系统 Logo 及"国家统计局泰兴调查队公文处理系统"；右侧展示当前用户全称、科室信息，以及包含通知唤醒中心的铃铛图标（显示被驳回或任务完成的未读角标）。
* **侧边菜单 (Sider)**：宽度 `240px`，政务蓝（或深色主题）。垂直导航。对应上方路由结构的几大一级模块入口。
* **底部状态基座 (Footer)**：固定高度 `24px`，深灰色底。
    * 左下角：通过 `/api/v1/sys/status` 暴露的 AI 引擎探针状态（🟢 在线 / 🔴 离线）。
    * 右下角：全局版权与声明。如果在工作区内，还会追加显示当前正文字数汇总（字数统计口径：剔除 Markdown 语法标记符号后的纯中英文字符数，由统一的 `utils/wordCount.ts` 提供）。

### 2. 个人工作台 (Dashboard View)
页面分列为左右双栏瀑布流或顶部数据卡片 + 下方双栏。
* **顶部快捷栏**：放置醒目的高亮发散按钮【➕ 起草新公文】（点击弹出"新建公文"对话框，**用户必须选择公文文种**（`Select` 下拉，调用 `GET /api/v1/doc-types` 获取选项），确认后触发 `POST /init` 并携带 `doc_type_id`，分配 `doc_id` 后路由跳转工作区）。
* **任务聚焦板 (Focus Board)**：
    * 若拥有审批权限：展示【待我签批】列表。
    * 个人事务：展示【我的公文任务】（包含正在进行的润色/排版进度）及【被驳回的公文】列表（红色标识驳回理由，附带一键唤醒 `revise` 回退编辑的按钮）。
* **异步任务中心 (GlobalTaskCenter)**：展示全局所有异步任务（POLISH/FORMAT/PARSE）的实时进度条、状态及错误堆栈。支持对 `FAILED` 任务发起重试。
* **近期处理台**：最近修改的 `DRAFTING` 状态的公文轮播列表页，方便接续草拟。

### 3. 沉浸式公文工作区 (Workspace View - 核心心脏)
采用极其克制的无边框拟物风格结构。屏蔽全局左侧通用 Sider，进入全屏沉浸空间。

* **左翼侧边栏 (VirtualDocTree)**：宽度弹性容纳（约 `280px`）。截断保护防撑爆：树节点必须注入 `min-width: 0` 和 `text-overflow: ellipsis`。下挂通过 `/api/v1/kb/hierarchy` 拉取的活体知识库目录树。叶子节点旁带有 Checkbox。用户在此处勾选往期台账或参考样表，直接作为短记忆 RAG 挂载上下文域（`context_kb_ids`）。
  * **参考范文区（Exemplar Panel）**：侧边栏底部增加"📄 参考范文"折叠面板，默认展开。根据当前公文的 `doc_type_id` 自动从 `GET /api/v1/exemplars?doc_type_id=xxx` 获取对应文种的范文列表（`tier` 按权限过滤）。以 Radio 单选控件展示（一次只能选一份），选中时将 `exemplar_id` 写入 `useEditorStore.exemplarId`，同时展示范文标题与文种标签。置空按钮允许取消选择。
* **顶部指挥带 (Action Bar)**：
    * 若处于**只读模式**：必须严格将 UI 状态拆分为以下两种互斥情况展示横幅，并拦截切断下方一切写入按钮与入口：
      1. **`READONLY_CONFLICT`**：由获取锁失败 409 冲突触发，居中黄色全宽警戒横带显示“XX 正在编辑，当前只读”。
      2. **`READONLY_IMMUTABLE`**：由 `document.status !== 'DRAFTING'` 触发，居中灰色或蓝色横带显示“公文已归档/流转中，不可编辑”。
      只读模式的核心判定策略必须遵循：**锁获取结果**为编辑权限的刚性控制优先级（强一致性）；而 `document.status` 的读取仅用于不可变状态的**辅助 UI 提示**判定（最终一致性）。
    * **操作按钮列**：左侧为返回及状态灯，同时显示只读的**文种标签**（如"通知"、"请示"，初始化时已锁定，`SUBMITTED` 后不可改）。中区提供 `[历史快照 ⏱]` 唤醒兜底系统。右侧放置业务器：紫金色的 `[AI 智能润色]`、`[GB国标排版并下载]` 及起草流收尾的 `[提交审批]`。所有并排按钮包裹防折行容器内。若公文处于 `APPROVED` 状态且排版产物 `word_output_path` 存在，排版按钮替换为 `[下载国标文档 📥]`；若排版任务 `FAILED`，则显示`[重新排版]`（橙色警示）。
* **中央纸基承载域 (Scroll Container)**：通过 A4 引擎呈现拟真物理白纸，深厚投影灰色托底（详见第四章 A4 引擎细则）。
* **右侧扩展区**：隐式加载的 `Drawer` 等部件储备层。

### 4. 统计知识资产库 (Knowledge Base Admin)
类似企业云盘视图设计，分为顶部统计筛选区和底端详细文件管廊。
* **资源分仓顶导 (Tabs)**：`[ 个人沙箱库 ] | [ 科室共享库 ] | [ 全局基础库 ] | [ 参考范文 ]` （根据 `useAuthStore` 控制权限灰显锁定与否）。
* **内容视图与操作**：展现资产名、按 `file_version` 定义的版本号与 `CORE`/`IMPORTANT` 红黄徽章。悬浮执行版调配更新、触发弹窗确认级联 DAO 软删除或实时观望解析 `PARSE` 小圆环状态等功能。
* **参考范文 Tab（Exemplar Library）**：
  * 顶部提供按文种（`doc_type_id`）过滤的下拉筛选，以及"上传新范文"按钮（权限：管理员 `role_level>=99` 或科室负责人 `dept_head_id`，且**仅接受 `.docx` 格式**）。
  * 列表展示范文卡片：标题、文种标签、上传者、上传时间。悬浮提供"预览文本"（调用 `GET /api/v1/exemplars/{id}/preview`，弹出 Modal 展示提取的纯文本）和"软删除"操作（删除前后端检查草稿引用，有引用则拒绝并提示）。
  * 上传流程：弹出上传 Drawer → 选择文件（`.docx` 格式限定）→ 填写范文标题 → 选择关联文种 → 确认上传。后端处理完成后刷新列表。

### 5. 科长签批管控台 (Approval Board)
界面必须呈现严谨庄重的复核体感环境结构。仅向具备负责人角色展现。
* **左列信件堆栈 (Inbox List)**：采用 List 结构显示状态皆为 `SUBMITTED` 的公文条目。
* **右域深核查视窗 (Audit View)**：全宽度展现该文终版底图快照。下挂判定决策盘：`[ 驳回打回 ]` (触发驳回缘由必填拦扣窗) 以及具备重度警戒弹窗保护宣告产生 SIP 核身凭证指纹的 `[ 批准并签署 ]`。

### 6. HRAG 穿透式智能问答 (Chat Center)
融合传统 Chat 且支持复杂领域数据限制范围的面板。
* **左置历史流 (History)** 及 **右置悬浮树 (Scoped Panel)** （提供挂钩检索边界限定）。主对话区采用 ToolTips 展示引用自某个特定 `<CHUNK>` 特征块的确切台账截留坐标。并具备应对查询失焦的硬干预话术“未探明对应统计线索”等降级展位。

### 7. 系统中枢设置 (System Settings Console)
承担全系统的权限治理、安全审计、AI 配置及底层基建参数监控。采用**左侧垂直 Tab 导航 + 右侧内容区**的主从布局，依据用户权级呈现阶梯式功能展现（`role_level >= 5` 可见审计相关 Tab，`role_level >= 99` 可见全部 Tab）。

#### 7.1 用户管理 (`role_level >= 99`)
表格 CRUD 全部用户：工号、真实姓名、所属科室（下拉）、`role_level`（1/5/99 单选）、`is_active` 开关、密码重置按钮（弹窗二次确认）。停用用户时弹出警告"该用户将无法登录和执行任何操作"。停用后该用户后续所有请求返回 HTTP 403。

#### 7.2 科室管理 (`role_level >= 99`)
表格 CRUD 科室：科室名称、编码、科室负责人（`dept_head_id`，下拉选本科室用户）、`is_active` 开关。删除前检查关联用户和公文，有则拒绝（仅允许停用）。

#### 7.3 公文文种管理 (`role_level >= 99`)
表格展示 `document_types` 全部文种（含通用文档/调研分析/经济信息）：文种编码、中文名、`layout_rules` JSON 预览、启停开关。点击"编辑"弹出 Drawer，内含 Monaco JSON 编辑器，可编辑 `layout_rules`。"新增文种"按钮：输入编码、名称、`layout_rules` JSON。禁止删除已有引用的文种（改为软停用）。

#### 7.4 提示词管理 (`role_level >= 99`)
列表展示 `app/prompts/` 下所有文件名（`system_chat.txt`、`system_polish.txt` 等）及最后修改时间。点击文件名展开 Monaco 编辑器（纯文本模式），支持在线修改。保存前弹出 `Popconfirm`（"确认保存并热加载此提示词？此操作将立即影响所有 AI 输出"）；保存后自动调用 `POST /api/v1/sys/reload-prompts`；每次修改写入审计日志（记录操作人、时间、文件名）。右侧固定展示占位符参考面板（`{context}`、`{exemplar_text}`、`{doc_type_name}` 等含义说明）。

#### 7.5 审计日志查询 (`role_level >= 5`)
多条件筛选面板：公文 ID、操作人、时间范围、工作流节点类型（下拉）。表格分页展示 `nbs_workflow_audit` 记录。支持"导出 CSV"按钮。科长仅可查询本科室相关日志；管理员可查全局。

#### 7.6 安全存证查询 (`role_level >= 5`)
查询 `document_approval_logs` 存证记录。提供"校验 SIP 哈希"按钮：输入 `doc_id`，调用 `GET /documents/{doc_id}/verify-sip`，返回 ✅ 一致 / ❌ 被篡改，结果高亮展示。

#### 7.7 锁监控大盘 (`role_level >= 99`)
实时列表展示 Redis 中所有活跃的 `lock:{doc_id}` 记录：锁定者姓名、文档标题、锁定时长、TTL 剩余秒数（进度条）。每行提供红色"强制释放"按钮（`DELETE /locks/{lock_key}`），操作前弹出 `Popconfirm`，操作后写审计日志，被驱逐用户收到 `LOCK_RECLAIMED` SSE 事件强制进入只读模式。

#### 7.8 任务监控大盘 (`role_level >= 99`)
表格展示 `async_tasks` 全部记录，支持状态筛选（QUEUED/PROCESSING/COMPLETED/FAILED）。FAILED 行高亮红色，提供"查看错误堆栈"（Drawer 展示 `error_message`）和"重试"按钮（`retry_count < 3` 时可用）。提供批量"肃清"按钮（将 FAILED 任务标记为已处理，不删除记录）。

#### 7.9 系统参数配置 (`role_level >= 99`)
表单化配置管理，持久化至 `system_config` 表（调用 `PUT /api/v1/sys/config`），服务重启后不丢失：

| 参数名 | 默认值 | 说明 |
|---|---|---|
| 编辑锁 TTL（秒） | 180 | 锁超时时长 |
| 心跳间隔（秒） | 90 | 锁续期频率 |
| Ollama HTTP 超时（秒） | 120 | AI 推理超时阈值 |
| AI 限流（次/分钟/用户） | 5 | 防恶意刷接口 |
| 自动保存间隔（秒） | 60 | 草稿自动保存频率 |
| 任务最大重试次数 | 3 | Celery 重试上限 |
| GIN 索引清理批次大小 | 5000 | 软删除切片置空批次 |

每项参数附带说明文字与合理范围校验（如锁 TTL 最小 30 秒，最大 600 秒），保存后即时生效。

#### 7.10 系统健康监控 (`role_level >= 99`)
Dashboard 卡片布局（调用 `GET /api/v1/sys/status`）：
- 🟢/🔴 数据库连通性（`db_connected`）
- 🟢/🔴 Redis 连通性（`redis_connected`）
- 🟢/🔴 Celery Worker 活跃数（`celery_workers_active`）
- 🟢/🔴 AI 引擎在线（`ai_engine_online`）
- 📊 CPU 使用率 / 内存使用率（进度条）
- 📦 `pg_dump` 最新快照时间与状态

#### 7.11 数据库快照管理 (`role_level >= 99`)
**快照列表**：表格展示历史快照文件（`GET /api/v1/sys/db-snapshots`）：快照时间、文件大小、触发人、状态（进行中/完成/失败）。
- **创建快照**：点击"立即备份"按钮（`POST /api/v1/sys/db-snapshot`），触发后端异步 `pg_dump` 任务，进度通过 SSE 或轮询展示。操作写审计日志。
- **恢复快照**：每行提供"恢复此快照"按钮（`POST /api/v1/sys/db-snapshots/{snapshot_id}/restore`）。**恢复操作必须经过双重确认**：第一步弹出 `Popconfirm` 说明"恢复操作将覆盖当前全量数据，操作不可逆，请确保已备份最新数据"；第二步要求用户在文本框中手动输入 `CONFIRM` 字样方可解锁执行按钮。操作执行后写 `CRITICAL` 级别审计日志。
- **存储说明**：快照文件默认存储于服务器 `ARCHIVE_ROOT` 目录，前端展示文件路径和大小供管理员参考。

#### 7.12 文件清理 (`role_level >= 99`)
操作面板：
- "清理临时文件"按钮（`POST /api/v1/sys/cleanup-cache`），展示上次执行时间与清理文件数。
- "扫描孤立物理文件"按钮（`POST /api/v1/sys/scan-orphan-files`），查找无逻辑节点引用的 `knowledge_physical_files` 记录并列出，提供批量删除。
- "GIN 索引维护"按钮（`POST /api/v1/sys/gin-maintenance`），手动触发软删除切片的 content 置空操作，展示影响行数。

### 8. 沉浸式工作区 - 高精度锁控策略 (Lock Guard)
* **Web Worker 心跳**：`useLockGuard` 必须启动一个 Web Worker 运行 `setInterval`。确保心跳请求不被浏览器节流（Throttling）干扰。
* **续期校准**：心跳成功后，依据后端返回的 `next_suggested_heartbeat` 校准下次执行时间，并将 `lock_ttl_remaining` 同步至 UI 状态栏。

* **生命周期闭环**：`beforeunload` 时使用 `fetch` 搭配 `keepalive: true` 发送最后一次心跳与释放。严禁使用 `sendBeacon`，因其无法携带复杂的认证 Header。

### 8. 统计知识资产管理 (Knowledge Management)
*   **三级分仓树**：左侧提供 `PERSONAL/DEPT/BASE` 的切换 Tab，支持点击展开、右键菜单（上传到此处、新建文件夹、重命名、替换上传、删除）。
*   **权限响应**：非科室负责人或管理员，`DEPT`/`BASE` 的写入操作应自动隐藏或禁用。
*   **多模式上传交互**：支持文件多选、文件夹拖拽及 `.zip/.tar.gz` 压缩包上传。上传时弹出抽屉，用户必须选择“安全等级”。
*   **状态实时同步**：通过 SSE 监听解析进度（`UPLOADED` -> `PARSING` -> `READY`）。
*   **关联起草**：勾选节点时，前端调用 `GET /snapshot-version` 捕获当前目录树的时间轴版本号，供 `polish` 请求提交。

---

## 四、 核心拟物化引擎与工作区交互 (A4 Engine & Behaviors)

### 1. A4 画板计算核心 (A4 Engine)
* **物理尺寸锁定**：编辑器容器被设定为绝对物理白纸大小。
  ```css
  .a4-paper {
    width: 794px; /* A4 纸张 210mm 的 96DPI 像素换算 */
    min-height: 1123px;
    background: #fff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    margin: 0 auto;
    padding: 72px 90px; /* 国标上下左右页边距近似值 */
  }
  ```
* **动态 Transform 防变形**：监听外层滚动容器的 `container.clientWidth`。精确计算 `scale = container.clientWidth / (794 + 180)`（此处 180 已内减容器 padding 和预留滚动条安全宽度影响值，避免触发意料外的横向溢出滚动）。**设定最小缩放系数为 0.5**。若计算值低于此阈值，则画板停止缩小并强制转换为横向滚动模式，同时悬浮提示用户切换横屏或大屏设备。外层施加 `transform: scale(var(--scale))`。

### 2. 双模态与沉浸交互 (SINGLE / DIFF Mode)
* **状态机设计**：`viewMode: 'SINGLE' | 'DIFF'`，持久化至 Zustand `persist`，刷新不丢失。
* **单栏模式 (SINGLE)**：纯净起草。只渲染一个挂载在 A4 画板上的富文本/Markdown 编辑器（编辑器组件在向下输出时，必须强行进行 Markdown 序列化转换，始终维持 `content` 字段纯净 Markdown 文本的绝对单一数据源）。
* **比对模式 (DIFF)**：当接收到 AI 润色结果时自动切换。
  * **左栏 (只读原稿)**：宽度占比 50%，背景色呈极浅的灰色 (`#fafafa`)，光标设为 `not-allowed`。
  * **右栏 (实时可写建议稿)**：宽度占比 50%，新增内容高亮展示。用户可直接在建议稿上进行二次修改。
  * 底部提供常驻的「接受并合并」和「丢弃」悬浮按钮（Floating Action Button）。
* **DIFF 模式退出逻辑**：
  * **接受并合并**：用户点击后，调用后端 `POST /api/v1/documents/{doc_id}/apply-polish`，并将右栏的最终修改稿作为 payload 的 `final_content` 提交。成功回调后，彻底切断前序干预动作（后端会先备份当前 `content` 原值生成快照，再用 `final_content` 覆写正文并清空临时建议态） → 前端无需再行任何额外 API 快照推送（完全信赖云端机制） → `viewMode` 闭合切回 `SINGLE`，清空状态机中的 `ai_polished_content`。
  * **丢弃**：二次确认 (Popconfirm) → 调用 `POST /api/v1/documents/{doc_id}/discard-polish` 接口阻断追踪 → 直接切回 `SINGLE` 模式 → 原文不变 → 清空状态机中的 `ai_polished_content`。

---

## 五、 异步交互与防断连中枢 (Async & SSE UX)

由于 AI 推理与文档排版均是长耗时操作，前端必须实现"发后即忘"（Fire-and-Forget）的非阻塞体验。

### 1. 公文管理中心 (Document List View)
* **常驻操作**：
    * `[查看/编辑]`：点击进入工作区。
    * `[下载 📥]`：仅 `APPROVED` 状态可见。
    * `[前往修改]`：仅 `REJECTED` 状态可见，触发 `POST /revise`。
* **批量操作**：支持勾选后批量软删除。

### 1. 骨架安抚动画 (Skeleton Pacifier)
在触发"润色"或"排版"但任务仍在 `QUEUED` 或 `PROCESSING` 阶段时，在 A4 画板的正中央覆盖一层带有高斯模糊（`backdrop-filter: blur(2px)`）的加载层，并渲染从上至下扫描的 Ant Design `Skeleton` 动画，辅以文字"AI 正在研读挂载台账，请稍候..."。

### 2. 全局无头守望者 (`GlobalTaskWatcher.tsx`)
* **隐身组件**：挂载在 `<App />` 的最顶层结构中，不占据任何 DOM 视觉空间。
* **职责与通信**：全局监听 `useTaskStore` 中的活跃任务，此囊括文档队列甚至 `PARSE` 切片行为。先发起请求体附带 `{"task_id": "uuid"}` 去 `/api/v1/sse/ticket` 开具 Ticket 随后叩动 EventSource 源头建立通道防泄密截获。**建立严苛的多路并行业务轨**：以 `task_id` 为映射 Key 维护多实例 EventSource 句柄表；管控最大并发 SSE 连接池（如上限必须设定为 `≤5`），若跨过峰值强制挂起并警告排队；一旦任意单体任务接收到 `COMPLETED`、`FAILED` 断语后，立刻注销关闭特定的 EventSource 流道封堵内存外泄并卸载轮询。
* **闭环接管通知**：一旦接收到 `COMPLETED`，右下角弹出 Notification 通知卡片。
    * **润色任务**：文案为“公文《xxx》的AI润色已完成。点击查看详情”。提供“查看详情”按钮（跳转至工作区并开启 DIFF）及“忽略”按钮。
    * **排版任务**：文案为“公文《xxx》国标排版已完成，点击下载”。提供“立即下载”按钮。
    * **失败任务**：文案为“任务《xxx》执行失败，请前往任务中心查看”。提供“前往处理”按钮。
* **断线补偿**：连接若是发生 `onerror` 被驱离时，必须在退避静默期间辅以发向底层 `task/status` 轮调询问同步可能流落未触发到前端队列中的迟点包裹。

### 3. 驳回与锁回收通知交互
* **驳回通知**：起草人收到 SSE 消息时，弹出 `notification.warning` 显示驳回理由，附带 `[前往修改]` 按钮触发 `revise`。
* **锁被动回收 (Reclaim Notification)**：当后端因他人抢占（如驳回重起草）或管理员强制释放锁时，通过 Redis Pub/Sub 向个人通知通道发布 `LOCK_RECLAIMED` 事件。前端通过专用 `useEditorNotifications` Hook 监听并响应：
  * `useEditorNotifications` 负责维护一条**个人级 SSE 长连接**（调用 `GET /api/v1/sse/user-events`，通过 `POST /api/v1/sse/ticket` 换取绑定 `user_id` 的 Ticket）。该连接独立于任务 SSE 连接池，不占用最大 5 路并发配额，随用户登录状态保持存活。
  * 前端监听到 `LOCK_RECLAIMED` 事件后，必须立刻执行以下动作：
  1. 弹出 `modal.error` 提示"您的编辑权限已被回收（原因：xxx），当前已进入只读模式"。
  2. 将 `Editor` 组件设为 `readOnly: true`。
  3. 禁用所有保存与提交按钮。


---

## 六、 状态中枢与后悔药机制 (Zustand Stores)

前端数据流必须单向、可追溯且具备防灾恢复能力。

### 1. `useEditorStore` (公文生命周期库)
* `currentDocId: string | null`
* `docTypeId: number | null` (当前公文文种 ID，创建时写入，工作区全程只读，仅用于过滤范文列表)
* `exemplarId: number | null` (当前选中的参考范文 ID，随 `POST /tasks/polish` 请求体一并提交)
* `content: string` (当前编辑器正文：在 DIFF 模式下，本段必须唯一指代左栏只读原稿，**严禁使用右栏内容污染 `content`**)
* `aiPolishedContent: string | null` (AI 润色建议稿，用于 DIFF 模式)
* `viewMode: 'SINGLE' | 'DIFF'` (双模态状态)
* `context_kb_ids: number[]` (当前勾选的知识库目录树节点 ID 数组)
* `context_snapshot_version: number` (勾选时从后端 `GET /api/v1/kb/snapshot-version` 接口获取的目录树版本号时间戳，用于防御目录树竞态；提交润色请求时随请求体一并发送)
* `saveFailureCount: number` (保存失败计数器)
* `lock_ttl_remaining: number` (锁剩余秒数，由后端自动保存/心跳响应更新)
* **自动保存与 DIFF 模式草稿双轨保护**：在常规 `SINGLE` 模式下，定时器必须且只能在 payload 中携带 `{"content": "..."}` 键发送至 `/auto-save`。进入 `DIFF` 模式时，先检查服务端 `draft_suggestion` 恢复，若空再检查 LocalStorage 缓存。在此模式下，定时器停止云端 `content` 同步，必须将右栏建议稿加密存入 `localStorage`（仅作崩溃极速恢复），同时调用专门针对此场景的 `POST /api/v1/documents/{doc_id}/auto-save` 并**严格限定 payload 仅包含 `{"draft_content": "修改后的建议稿"}` 键（防呆过滤 `content` 键，避免触发后端 DIFF 保护拦截）**，将数据持久化推送到云端的 `draft_suggestion` 字段（主存储，用于跨终端恢复）。**请注意此处的架构权衡限制：由于 `draft_suggestion` 是单值字段，DIFF 模式下的每次自动保存只会覆盖最新的一份草稿，无法像 `content` 那样实现多版本的快照追溯**。在 `useEditorStore` 中，`persist` 机制利用 `partialize` 筛选，严格保证只会存储最近 2 次的本地快照序列以作短效极速恢复。
* **云端后悔药机制 (Cloud Snapshot History)**：完全摒弃单机历史。在执行“接受润色”等操作前，**后端会自动创建备份快照**，前端仅需配合展示。列表拉取支持 `(page=1, page_size=20)` 分页。

### 2. `useAuthStore` (用户鉴权库)
* 存储 `token`、`userInfo`。提供 `logout()`。当全局拦截到 `401 Unauthorized` 自动路由至 `/login`。

### 3. `useTaskStore` (任务监控库)
* `activeTaskIds: string[]` / `taskResults: Record<string, any>`：监管长耗时事件与处理失败回退节点。

---

## 七、 灾备恢复窗口与隔离互斥降维锁 (`Recovery & Locks`)

### 1. 抽屉历史回放区 (`SnapshotRecoveryDrawer.tsx`)
在工具栏放置「历史快照 ⏱」触发右侧 Ant Design `<Drawer>` 抽屉面板。
* 在前端展示拉取列表时，由于云端储量可能无限化叠加，提取请求必须默认挂接带有 `(page=1, page_size=20)` 约束的参数发往后端防撑爆内存。
* 显示快照的时间、引发快照存入的原因行为（如接受覆盖、五分钟留档），供点击触发重载恢复。
* 选择覆盖恢复前由 `<Popconfirm>` 中拦二次核查阻拦危险手误。当确定覆写旧案时，同时调用 `POST /api/v1/documents/{doc_id}/snapshots` 再发起一次当前最新画板上存在的“快照备灾保存动作”，严丝合缝拦截全量误删意外。

### 2. 隔离冲突死锁警戒仪 (`LockConflictBanner.tsx`)
* **锁获取与维持策略**：
  * **延时预占**：新建公文跳转至 `/workspace/:doc_id` 后，不立即申请锁。仅当用户第一次产生输入行为、粘贴内容或焦点进入编辑器时，由 `useLockGuard` 触发 `POST /api/v1/locks/acquire`。
  * **心跳与续期**：基于 `GET /api/v1/locks/config` 下发的频率（默认 90s）发送 `POST /locks/heartbeat`。
  * **只读降级**：
    1. **`READONLY_CONFLICT`**：获取锁 409 冲突。黄色横幅提示“XX 正在编辑，当前只读”。
    2. **`READONLY_IMMUTABLE`**：公文状态非 `DRAFTING`。蓝色/灰色横幅提示“公文流转中，不可编辑”。
  * **自动恢复**：只读模式下引入指数退避（2s, 4s, 8s... 至 30s）自动重试 `acquire`。
* **卸载生死门兜底技术**：拦截 `window.beforeunload` 时，**统一使用 `fetch` 搭配 `keepalive: true`** 发射最后的自动保存与锁释放请求。后端接口必须适配此异步请求。

---

## 八、 全局防弹通用细节约束 (Bulletproof Nuances)

1. **操作台折行与加载锁定**：编辑器顶部的操作按钮包裹在折行容器中。**所有涉及 API 调用的操作（尤其删除/丢弃）必须挂载 `loading` 状态并配合 `disabled`属性**，防止重复提交及视觉闪烁。
2. **绝对拦扣危险动作框**：所有的"删除"、"清空公文"、"终止任务"、"丢弃建议"均需搭载 `<Popconfirm>` 强制核实。
3. **令牌静默续期**：`apiClient` 在捕获 `401 Unauthorized` 时，自动发起 `POST /auth/refresh` 使用 HttpOnly Cookie 中的 Refresh Token 申请新 Access Token 并在恢复后无感重发失败请求。
4. **水印与滚动条标准化**：... (略)
5. **表格解析态渲染**：知识库树节点依据 `parse_status` 动态展示加载态，阻断对 `PARSING` 状态文件的越权访问尝试。