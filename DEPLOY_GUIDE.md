# 泰兴调查队公文处理系统 V3.0 - 部署与运维全案手册

> **项目定位**：国家统计局泰兴调查队工业级公文处理中枢。
> **版本**：V3.0 (极致匠心版)
> **编写日期**：2026-05

---

## 一、 环境架构概览

| 特性 | 开发环境 (Development) | 生产环境 (Production) |
| :--- | :--- | :--- |
| **操作系统** | Windows 11 + Docker Desktop | Ubuntu 24.04 Server LTS |
| **服务器 IP** | 10.132.60.133 (本机) | 10.132.60.111 |
| **容器编排** | `docker-compose.dev.yml` | `docker-compose.yml` |
| **AI 算力** | 本地 Ollama (gemma4:e4b) | 远程 Ollama (10.132.60.111) |
| **网络模式** | 端口全暴露 (8000, 5432, 6379) | 仅暴露 Nginx (80, 443)，内部网络隔离 |
| **卷挂载** | Bind Mount (实时热重载) | Named Volume (物理持久化) + Prompts ro 挂载 |

---

## 二、 开发环境部署指南 (Local Machine)

### 1. 准备工作
- 确保已安装 **Docker Desktop** 并启用 WSL2 后端。
- 确保本地 **Ollama** 已启动并加载模型：`ollama run gemma4:e4b`。

### 2. 配置文件
复制并检查 `.env` 文件：
```bash
cp .env.example .env
```
确认 `OLLAMA_BASE_URL` 指向 `http://host.docker.internal:11434`。

### 3. 启动集群
在项目根目录下运行（Windows 不支持 &&，请分行执行）：
```powershell
docker compose -f docker-compose.dev.yml up -d --build
```

### 4. 数据库初始化
```powershell
# 执行迁移
docker compose -f docker-compose.dev.yml exec api alembic upgrade head
# 导入种子数据
docker compose -f docker-compose.dev.yml exec api python scripts/seed_data.py
```

### 5. 默认凭证 (重要)
- **最高权限账户 (Superuser)**: `admin`
- **默认密码 (Default Password)**: `Admin123`
- **注意**: 首次登录开发或生产环境后，请务必通过 [系统中枢设置] 进行安全审计确认。

---

## 三、 生产环境部署指南 (Remote Server)

### 1. 自动化交付 (在本机执行)
利用已配置的免密登录，将源码推送至服务器：
```powershell
# 建议通过 git clone 或 scp 传输
scp -r . zpf@10.132.60.111:/home/zpf/newgwsh
```

### 2. 环境变量硬化
在服务器上创建并编辑 `.env`：
```bash
cd /home/zpf/newgwsh
cp .env.prod.example .env
# 铁律：务必设置复杂的 SIP_SECRET_KEY 和 POSTGRES_PASSWORD
vi .env 
```

### 3. 一键启航
服务器已配置 Compose V2，请直接使用 `docker compose`：
```bash
docker compose up -d --build
```

### 4. 生产初始化 (首次部署)
```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_data.py
```

---

## 四、 极致匠心 - 运维铁律清单

### 1. 资产安全 (P0)
- **SIP 密钥**：`.env` 中的 `SIP_SECRET_KEY` 一经设定，**严禁修改**。修改将导致所有已通过公文的指纹校验失效。
- **CORE 密级**：任何情况下不得将 `CORE` 级切片移出内网或通过非 HTTPS 隧道传输。

### 2. 状态机自愈
- 若发现编辑锁死锁（如用户异常离线且心跳中断），管理员可通过 `[系统中枢设置]` 页面点击 **[强放]**。
- 手工清理 Redis 指令：`docker compose exec redis redis-cli del lock:<doc_id>`。

### 3. 异步任务监控
- 观察 `async_tasks` 大盘。若 `FAILED` 任务增多，检查 `api` 容器日志：`docker compose logs -f api`。
- 若 AI 响应变慢，可扩容 Worker：`docker compose up -d --scale worker=3`。

### 4. 备份策略
- **每日全备**：建议每日凌晨执行 `pg_dump`。
- **快照备份**：系统在 `apply-polish` 前会自动创建快照，可在 Workspace 右侧抽屉回滚。

---

## 五、 常见故障排查 (Troubleshooting)

| 现象 | 原因 | 修复方案 |
| :--- | :--- | :--- |
| 登录返回 500 | 数据库未就绪或 .env 路径错误 | 检查 `POSTGRES_HOST` 是否为 `db` |
| AI 润色一直转圈 | Celery Worker 未启动或无法连接 Ollama | 执行 `docker compose ps` 查看 worker 状态 |
| A4 画板显示错位 | 浏览器缩放非 100% | 调整浏览器缩放，或依赖系统的 `transform: scale` 自适应 |
| SIP 校验不一致 | 公文正文被非法直接篡改数据库 | 属于安全事件，请通过审计日志追溯操作人 |

---
*国家统计局泰兴调查队 - 极致匠心公文系统 V3.0 技术委员会*
