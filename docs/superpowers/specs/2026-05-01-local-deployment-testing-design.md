# 本机部署与 Playwright 物理测试设计方案

## 1. 目标
在本机环境（Windows）中完整部署 NewGWSH 系统，并建立一套基于 Playwright 的端到端（E2E）自动化测试程序，确保系统核心链路（登录、知识库管理、AI 问答）功能正常。

## 2. 部署架构 (混合模式)
- **基础设施 (Docker)**: 仅运行 PostgreSQL (含 pgvector) 和 Redis。
- **后端 (Native)**: Python 3.10+, 运行 Uvicorn (API) 和 Celery (Worker)。
- **前端 (Native)**: Node.js, 运行 Vite 开发服务器。
- **AI (Ollama)**: 调用本机已安装的 Ollama 服务，模型指定为 `gemma4:e4b`。

## 3. 详细设计

### 3.1 基础设施准备
- 使用 `docker-compose.yml` 启动 `db` 和 `redis` 容器。
- 验证 pgvector 插件是否正常加载。

### 3.2 后端部署
- **环境**: 创建 `.venv` 虚拟环境。
- **依赖**: 安装 `requirements.txt`。
- **配置**: 创建 `.env` 文件，确保以下关键项配置正确：
  - `POSTGRES_HOST=localhost`
  - `REDIS_URL=redis://localhost:6379/1`
  - `OLLAMA_MODEL=gemma4:e4b`
  - `STORAGE_ROOT=data/storage`
- **初始化**: 运行数据库迁移或初始化脚本。

### 3.3 前端部署
- **环境**: 进入 `frontend` 目录。
- **安装**: `npm install`。
- **启动**: `npm run dev` (默认端口 5173)。

### 3.4 物理测试 (Playwright E2E)
- **目录**: `tests/e2e/`。
- **测试栈**: Playwright (Python 或 Node.js 接口，根据方便程度选择，本方案优先考虑 Python 接口以便于与后端逻辑集成)。
- **关键测试用例**:
  1. **Login Flow**: 模拟输入用户名密码，验证重定向到仪表盘。
  2. **Knowledge Base CRUD**: 创建知识库 -> 重命名 -> 删除。
  3. **File Management**: 上传测试文档，检查解析状态。
  4. **AI Chat Loop**: 发送提问，验证 AI 是否返回有效响应（基于 `gemma4:e4b`）。
  5. **UI Integrity**: 检查导航栏、侧边栏和关键按钮的可点击性。

## 4. 成功标准
- 所有 Docker 容器状态为 Healthy。
- 后端服务启动无 Error 级别日志。
- 前端页面在浏览器可正常访问。
- Playwright 测试套件运行通过率 100%。

## 5. 风险与约束
- 本机 5432/6379/8000/5173 端口不得被占用。
- Ollama 需要在测试期间保持开启。
