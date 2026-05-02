# 本机部署与 Playwright 物理测试实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在本机环境完成系统部署并运行 Playwright 端到端测试。

**架构：** 混合部署模式：Docker 运行 DB/Redis，本机运行 API/Worker/Vite。

**技术栈：** Python 3.10+, FastAPI, Node.js, Vite, Playwright, Docker, Ollama.

---

### 任务 1：启动基础设施 (Docker)

**文件：**
- 修改：`docker-compose.yml` (确认配置)

- [ ] **步骤 1：检查 docker-compose.yml**
确保 db 和 redis 服务配置正确，端口 5432 和 6379 映射到主机。

- [ ] **步骤 2：启动容器**
运行：`docker-compose up -d db redis`
预期：`db` 和 `redis` 容器状态为 running。

- [ ] **步骤 3：验证数据库连接**
运行：`docker ps` 确认容器运行，并尝试简单的端口探测。

---

### 任务 2：后端环境配置

**文件：**
- 创建：`.env`
- 修改：`requirements.txt` (如果需要补全 playwright)

- [ ] **步骤 1：创建 .env 文件**
从 `.env.example` 复制并修改：
```bash
copy .env.example .env
```
修改内容：
- `POSTGRES_HOST=localhost`
- `OLLAMA_MODEL=gemma4:e4b`
- `STORAGE_ROOT=data/storage`

- [ ] **步骤 2：创建 Python 虚拟环境**
运行：`python -m venv .venv`

- [ ] **步骤 3：安装依赖**
运行：`.venv\Scripts\activate && pip install -r requirements.txt playwright pytest-playwright`

---

### 任务 3：数据库初始化

**文件：**
- 修改：`scripts/seed_data.py` (确认逻辑)

- [ ] **步骤 1：运行数据初始化脚本**
运行：`.venv\Scripts\python scripts/seed_data.py`
预期：日志显示成功创建用户、部门和基础配置。

---

### 任务 4：前端环境配置

**文件：**
- 目录：`frontend/`

- [ ] **步骤 1：安装依赖**
运行：`cd frontend && npm install`

- [ ] **步骤 2：验证前端构建**
运行：`npm run build` (可选，确保无语法错误)

---

### 任务 5：启动系统服务 (后台运行)

- [ ] **步骤 1：启动后端 API**
运行 (在后台或新窗口)：`.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

- [ ] **步骤 2：启动 Celery Worker**
运行 (在后台或新窗口)：`.venv\Scripts\celery -A app.tasks.celery_app worker --loglevel=info -P solo` (Windows 下建议使用 -P solo)

- [ ] **步骤 3：启动前端 Vite**
运行 (在后台或新窗口)：`cd frontend && npm run dev`

---

### 任务 6：配置与运行 Playwright 测试

**文件：**
- 创建：`tests/e2e/test_main_flow.py`
- 创建：`tests/e2e/conftest.py`

- [ ] **步骤 1：安装 Playwright 浏览器**
运行：`.venv\Scripts\playwright install chromium`

- [ ] **步骤 2：编写核心流程测试代码**
实现 `tests/e2e/test_main_flow.py`，包含以下步骤：
1. 访问 `http://localhost:5173/login`
2. 登录系统。
3. 进入知识库页面，创建测试知识库。
4. 上传测试文件。
5. 进入聊天页面，发送消息 "你好"，验证 AI 返回。

- [ ] **步骤 3：运行测试并生成报告**
运行：`.venv\Scripts\pytest tests/e2e/test_main_flow.py --headed --browser chromium`
预期：所有测试用例 PASS。
