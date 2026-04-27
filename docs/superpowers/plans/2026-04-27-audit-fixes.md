# 审计缺陷修复实施计划 (Audit Fixes Plan)

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 根据审计报告修复项目中的逻辑偏差、安全性隐患及低级语法错误，确保存证链条严密且系统运行稳定。

**架构：**
- 后端：增强 `DocumentService` 的原子锁逻辑，引入指纹校验，优化中间件 IP 识别。
- 前端：修正组件 JSX 结构，优化状态恢复的时序，收敛硬编码参数。

**技术栈：** FastAPI, React (TypeScript), Redis, PostgreSQL, Celery

---

### 任务 1：修复前端 JSX 语法错误 (阻断性问题)

**文件：**
- 修改：`frontend/src/components/Workspace/VirtualDocTree.tsx`

- [ ] **步骤 1：移除冗余的 JSX 闭合标签**

```typescript
// 找到文件末尾，移除多余的 </div>  ); };
```

- [ ] **步骤 2：验证组件正确性**

运行：`npm run type-check` (或确认 IDE 无红线)

### 任务 2：补全后端国标排版任务调用

**文件：**
- 修改：`backend/app/api/v1/endpoints/documents.py`

- [ ] **步骤 1：取消 `trigger_format` 中 Celery 任务的注释**

```python
# 找到 dummy_format_task.apply_async 并恢复
```

### 任务 3：重构驳回修改 (revise) 锁逻辑 (高风险)

**文件：**
- 修改：`backend/app/services/document_service.py`

- [ ] **步骤 1：改进原子抢锁逻辑**

修改 `revise_document`：
1. 移除不安全的“先 get 后 eval del”逻辑。
2. 使用 `SET lock_key value NX EX` 抢锁。
3. 若抢锁失败且原锁属于当前用户，则允许覆盖（容错）；若属于他人，则抛出 `DocumentLockedError`。

###  tarefa 4：后端自动保存指纹校验对齐

**文件：**
- 修改：`backend/app/services/document_service.py`

- [ ] **步骤 1：实现内容哈希比较**

```python
def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
```

修改 `auto_save` 方法，计算传入 content 的哈希并与现有内容对比，若一致则跳过数据库写操作。

### 任务 5：中间件 IP 识别增强 (代理支持)

**文件：**
- 修改：`backend/app/api/middleware.py`

- [ ] **步骤 1：支持 X-Forwarded-For**

```python
# 优先从 request.headers.get("X-Forwarded-For") 提取，取第一个 IP
```

### 任务 6：审计日志限制参数化

**文件：**
- 修改：`backend/app/api/v1/endpoints/audit.py`

- [ ] **步骤 1：使用 settings 配置代替硬编码**

```python
# .limit(50) -> .limit(settings.MAX_AUDIT_LOG_LIMIT)
```

### 任务 7：前端状态漫游闪烁优化

**文件：**
- 修改：`frontend/src/pages/Workspace.tsx`

- [ ] **步骤 1：使用批量状态更新或 Loading 占位符**

优化 `useEffect` 中的恢复顺序，或在恢复过程中设置 `loading` 状态。

### 任务 8：水印组件优化

**文件：**
- 修改：`frontend/src/components/Security/AntiLeakWatermark.tsx`

- [ ] **步骤 1：移除硬编码颜色，对齐配置**
- [ ] **步骤 2：移除秒级时间戳，仅保留日期**

---
## 自检清单
1. 规格覆盖：已涵盖审计报告中的所有【高】和【严重】项。
2. 占位符：无。
3. 类型一致性：保持现有 Pydantic 和 TypeScript 类型定义。
