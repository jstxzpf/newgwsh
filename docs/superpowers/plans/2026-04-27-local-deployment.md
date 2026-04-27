# 本地部署实现计划 (IP: 10.132.60.133)

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将泰兴市国家统计局公文处理系统部署到本地 IP 10.132.60.133，确保所有服务（DB, Redis, Backend, Worker, Frontend）正常运行。

**架构：** 使用 Docker Compose 进行容器化部署。Nginx 作为前端服务器并代理 API 请求到后端。

**技术栈：** Docker, Docker Compose, PostgreSQL (pgvector), Redis, FastAPI (Python), React (TypeScript), Nginx.

---

### 任务 1：准备部署环境

**文件：**
- 修改：`.env`
- 修改：`docker-compose.yml`

- [ ] **步骤 1：创建必要的本地目录**
确保数据持久化目录存在。
运行：`mkdir -p data/uploads data/archive`

- [ ] **步骤 2：检查并更新 .env 配置**
确保 `.env` 中的 IP 地址与目标一致（已确认为 10.132.60.133）。
检查 `OLLAMA_BASE_URL` 等关键配置。

- [ ] **步骤 3：验证 docker-compose.yml**
确认端口映射（80:80, 8000:8000, 5432:5432, 6379:6379）没有冲突。

### 任务 2：构建并启动服务

- [ ] **步骤 1：执行 Docker Compose 构建**
运行：`docker-compose build`
预期：构建成功，无错误。

- [ ] **步骤 2：启动所有容器**
运行：`docker-compose up -d`
预期：所有容器状态为 "Started"。

### 任务 3：验证部署状态

- [ ] **步骤 1：检查容器运行状态**
运行：`docker-compose ps`
预期：所有服务 (db, redis, backend, worker, frontend) 均为 Up 状态。

- [ ] **步骤 2：验证后端 API 健康检查**
运行：`curl http://localhost:8000/api/v1/sys/health`
预期：返回 JSON 包含 "status": "ok"。

- [ ] **步骤 3：验证前端访问**
访问：`http://10.132.60.133/`
预期：能够加载登录页面或主页。

- [ ] **步骤 4：检查后端日志是否有异常**
运行：`docker-compose logs --tail=100 backend`
预期：无明显错误日志。
