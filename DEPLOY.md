# 泰兴调查队公文处理系统 V3.0 - 生产部署指南

## 一、 服务器环境要求
- **OS**: Ubuntu 24.04 LTS (推荐)
- **Engine**: Docker Engine 24.0+ & Docker Compose V2
- **Hardware**: 4核 8G (最低) / 8核 16G (推荐，含本地 AI 引擎)

## 二、 部署步骤

### 1. 准备配置文件
```bash
# 复制并配置生产环境变量
cp .env.prod.example .env
vi .env  # 填入真实的 SIP_SECRET_KEY 和 数据库密码
```

### 2. 启动集群
```bash
# 一键构建并启动
docker compose up -d --build
```

### 3. 初始化数据库 (首次部署)
```bash
# 执行数据库迁移
docker compose exec api alembic upgrade head

# 导入基础台账及部门数据
docker compose exec api python scripts/seed_data.py
```

### 4. 验证服务
- 访问：`http://10.132.60.111`
- 审计日志查看：`docker compose logs -f api`

## 三、 极致匠心 - 运维铁律
1. **数据备份**：必须每日备份 `pg_prod_data` 卷中的 SQL 文件。
2. **SIP 保护**：`.env` 中的 `SIP_SECRET_KEY` 一经设定，**严禁修改**，否则所有已批准公文的指纹将失效。
3. **扩容建议**：若 AI 润色队列堆积，可增加 `worker` 服务实例：`docker compose up -d --scale worker=3`。

## 四、 紧急夺锁
若管理员需强制清理僵尸编辑锁，请通过 [系统中枢设置] 页面进行，或手动操作 Redis：
```bash
docker compose exec redis redis-cli del lock:<doc_id>
```
