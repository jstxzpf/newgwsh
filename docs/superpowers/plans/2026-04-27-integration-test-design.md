# 集成测试方案设计规格 (Integration Test Design Spec)

## 1. 目标 (Goals)
建立一套自动化、端到端、具备环境自愈能力的集成测试套件，确保“泰兴市国家统计局公文处理系统”的核心业务逻辑、AI 协同能力、SSE 安全机制及数据库一致性在真实运行环境下达到 100% 正确。

## 2. 环境要求 (Environment)
- **运行时**: Python 3.10+
- **测试框架**: Pytest + Pytest-asyncio
- **基础设施**: Docker Desktop (PostgreSQL, Redis)
- **AI 引擎**: 真实 Ollama 节点 (`10.132.60.133:11434`)

## 3. 架构设计 (Architecture)

### 3.1 环境自愈层 (Self-Healing Layer)
在测试 Session 开始前，通过脚本执行以下逻辑：
1. **容器检测**: 检查 Docker 中 `postgres` 和 `redis` 容器是否处于 `running` 状态。
2. **自动启动**: 若未运行，调用 `docker start`。
3. **拨测**: 确保端口 5432 和 6379 可连通，否则抛出环境异常。
4. **数据库隔离**: 
   - 自动创建 `test_taixing_nbs` 数据库。
   - 使用 Alembic 或 SQLAlchemy `create_all` 初始化表结构。

### 3.2 测试执行层 (Execution Layer)
- **API 客户端**: `httpx.AsyncClient`。
- **并发控制**: 支持并行测试（部分不涉及独占锁的用例）。
- **任务监控**: 针对异步 Celery 任务，采用“轮询-断言”模式（Poll & Assert），超时时间设为 120s。

## 4. 核心用例设计 (Core Test Cases)

### TC-01: 公文起草至签署全链路 (P0)
- **输入**: 模拟用户起草公文。
- **动作**: `init` -> `auto_save` -> `submit` -> `review`。
- **验证**: 
  - 数据库 `documents` 表状态流转符合 `DRAFTING -> SUBMITTED -> APPROVED`。
  - 审批通过后，`ai_polished_content` 必须已固化，且 `audit_logs` 中存在对应的 SIP 存证记录。

### TC-02: SSE Ticket 安全边界 (P0)
- **动作**: 
  1. 用户 A 创建任务并申请 Ticket。
  2. 用户 B 尝试携带 A 的 Ticket 请求 `/sse/{task_id}/events`。
- **验证**: 
  - 后端必须返回 `403 Forbidden`。
  - 用户 A 使用一次 Ticket 后，再次使用应返回 `403`（阅后即焚）。

### TC-03: 知识库解析与异常回滚 (P1)
- **输入**: 上传一个损坏的 Excel 或不支持的格式。
- **动作**: 触发 `parse_kb_file_task`。
- **验证**: 
  - 任务状态标记为 `FAILED`。
  - `knowledge_chunks` 表中不应残留该 KB 相关的任何脏切片数据（验证回滚 SQL 逻辑）。

## 5. 成功标准 (Success Criteria)
- 所有集成测试用例在本地 Docker 环境下 100% 通过。
- 能够自动处理数据库和 Redis 的启动，无需手动干预。
- 测试过程不产生残留的测试数据（测试库在结束后自动 Drop 或状态重置）。
