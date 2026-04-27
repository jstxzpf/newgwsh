# 2026-04-27 项目问题综合修复计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 修复项目中发现的 21 项功能、逻辑、语法及配置问题，并优化构建流程。

**架构：** 按照“Research -> Strategy -> Execution”流程，对后端 Service/Endpoint 层和前端 Component/Hook 层进行手术刀式修复，并调整 Docker 构建脚本。

**技术栈：** FastAPI, React (TypeScript), Celery, Redis, Ant Design, Docker.

---

### 任务 1：后端基础与语法修复 (Batch 1)

**文件：**
- 修改：`backend/app/api/v1/endpoints/documents.py`
- 修改：`backend/app/services/kb_service.py`
- 修改：`backend/app/services/document_service.py`

- [ ] **步骤 1：修复任务函数导入名错误**
    - 在 `documents.py` 中将 `dummy_format_task` 统一为 `format_document_task`。
- [ ] **步骤 2：解耦硬编码的上传路径**
    - 在 `kb_service.py` 中使用 `settings.UPLOAD_DIR` 替换硬编码路径。
- [ ] **步骤 3：下沉公文删除逻辑至 Service 层**
    - 在 `DocumentService` 中实现 `delete_document` 方法，包含软删除和锁释放逻辑。
    - 更新 `documents.py` 中的 `delete_document` 端点调用此方法。
- [ ] **步骤 4：运行基础测试验证**
    - 运行：`pytest backend/tests/integration/test_full_workflow.py` 确保核心流程未破坏。

### 任务 2：功能端点补全 (Batch 2)

**文件：**
- 修改：`backend/app/api/v1/endpoints/documents.py`
- 修改：`backend/app/api/v1/endpoints/audit.py`
- 修改：`backend/app/api/v1/endpoints/sys.py`
- 修改：`backend/app/api/v1/endpoints/tasks.py`

- [ ] **步骤 1：实现公文下载端点**
    - 在 `documents.py` 中添加 `GET /api/v1/documents/{doc_id}/download`。
- [ ] **步骤 2：审计日志支持时间筛选**
    - 在 `audit.py` 的 `get_audit_logs` 中增加 `start_time` 参数。
- [ ] **步骤 3：公文列表支持部门过滤**
    - 在 `documents.py` 的 `list_documents` 中增加 `dept_id` 参数。
- [ ] **步骤 4：补全系统配置端点**
    - 在 `sys.py` 中实现 `cleanup-cache` 和 `PUT /config`。
- [ ] **步骤 5：独立任务触发端点**
    - 在 `tasks.py` 中添加 `/polish` 和 `/format` 触发端点。

### 任务 3：核心逻辑深度加固 (Batch 3)

**文件：**
- 修改：`backend/app/tasks/worker.py`
- 修改：`backend/app/services/audit_service.py`
- 修改：`backend/app/services/kb_service.py`
- 修改：`backend/app/api/v1/endpoints/tasks.py`

- [ ] **步骤 1：基于 AST 的国标排版引擎升级**
    - 在 `worker.py` 的 `format_document_task` 中集成 `MarkdownIt` 识别标题层级。
- [ ] **步骤 2：知识库 Excel 解析元数据补全**
    - 在 `worker.py` 的 `parse_kb_file_task` 中记录行列 JSON 坐标。
- [ ] **步骤 3：审批通过唯一性约束**
    - 在 `DocumentService.review_document` 中增加逻辑，若已处于 APPROVED 态则报错。
- [ ] **步骤 4：知识库上传父目录鉴权下沉**
    - 在 `KBService.create_hierarchy_node` 中增加父目录权限检查。
- [ ] **步骤 5：补全重试逻辑与任务清理**
    - 在 `tasks.py` 的 `retry_failed_task` 中增加 `FORMAT` 分支。
    - 实现 `cleanup_expired_files_task` 中的物理文件清理 TODO。

### 任务 4：前端交互与安全性优化 (Batch 4)

**文件：**
- 修改：`frontend/src/hooks/useAutoSave.ts`
- 修改：`frontend/src/components/Security/AntiLeakWatermark.tsx`
- 修改：`frontend/src/components/Workspace/VirtualDocTree.tsx`
- 修改：`frontend/src/pages/Settings.tsx`
- 修改：`frontend/src/pages/Workspace.tsx`

- [ ] **步骤 1：实现卸载前自动保存与锁释放**
    - 在 `useAutoSave.ts` 中注册 `beforeunload` 事件。
- [ ] **步骤 2：安全脱敏水印**
    - 在 `AntiLeakWatermark.tsx` 中移除秒级/分钟级时间戳，仅保留日期。
- [ ] **步骤 3：前端类型安全修复**
    - 修复 `VirtualDocTree.tsx` 中的 `checkedKeys` 类型。
- [ ] **步骤 4：补全动态基建配置 UI**
    - 在 `Settings.tsx` 中增加基建配置表单。
- [ ] **步骤 5：实现国标排版产物下载逻辑**
    - 在 `Workspace.tsx` 中对接后端的下载端点。

### 任务 5：构建流程国内优化 (Batch 5)

**文件：**
- 修改：`backend/Dockerfile`
- 修改：`frontend/Dockerfile`

- [ ] **步骤 1：后端镜像优化**
    - 配置 Debian/Python (pip) 镜像源为清华源。
    - 优化 Layer 顺序实现最小变动构建。
- [ ] **步骤 2：前端镜像优化**
    - 配置 Alpine/NPM 镜像源为阿里源。
    - 优化多阶段构建。

---

**验证条件：**
1. 运行 `pytest` 所有集成测试通过。
2. 前端编译无类型警告。
3. 验证 `GB国标排版并下载` 功能可真实下载文件。
4. 验证水印不再包含具体时间。
