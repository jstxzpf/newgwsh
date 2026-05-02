# 2026-05-02 本地部署与物理测试程序设计方案

## 1. 概述
本文档详细描述了 NewGWSH 系统的本地部署方案及基于 Playwright 的自动化物理测试（E2E）程序设计。

## 2. 部署方案 (Docker Compose)
系统将采用 Docker Compose 进行一键部署，确保环境一致性。

### 2.1 组件架构
- **db**: 使用 `pgvector/pgvector:pg16`，支持向量搜索。
- **redis**: 使用 `redis:7.2.4-alpine`，作为 Celery 消息代理和锁管理。
- **api**: FastAPI 后端服务，运行在 8000 端口。
- **worker**: Celery 异步工作节点。
- **frontend**: Vite/React 前端应用（需要集成到 compose 中或通过本地 Node 运行，本方案建议通过本地运行以方便开发调试）。

### 2.2 Ollama 集成
- 后端通过 `OLLAMA_BASE_URL` 连接到宿主机运行的 Ollama 服务（通常为 `http://host.docker.internal:11434`）。
- 使用 `gemma4:e4b` 模型。

## 3. 物理测试程序设计 (Playwright + TypeScript)
测试程序将存放在项目根目录下的 `e2e-tests` 目录。

### 3.1 测试内容
1.  **前端展示测试**：验证登录页、仪表盘、知识库等核心页面的渲染情况。
2.  **API 连通性测试**：通过 UI 操作验证后端接口是否正确返回数据。
3.  **按钮功能测试**：遍历主要交互元素（如新建文档、提交审批、AI 聊天）。
4.  **完整业务流模拟**：
    - 用户登录。
    - 上传文档至知识库。
    - 使用 AI 进行文档内容对话。
    - 发起并完成一个简单的审批流程。

### 3.2 目录结构
```
e2e-tests/
├── tests/
│   ├── auth.spec.ts        # 登录认证测试
│   ├── chat.spec.ts        # AI 对话测试
│   └── workflow.spec.ts    # 业务全流程模拟
├── playwright.config.ts    # 测试配置
└── package.json            # 测试依赖
```

## 4. 实施步骤
1.  **环境配置**：更新 `.env` 文件以适配本地宿主机 Ollama。
2.  **启动服务**：使用 `docker-compose up -d` 启动基础架构。
3.  **安装测试环境**：在 `e2e-tests` 目录初始化 Playwright。
4.  **编写测试用例**：实现上述设计的测试场景。
5.  **执行与验证**：运行测试并生成报告。

## 5. 成功标准
- 所有 Docker 容器状态为 Healthy。
- 后端能成功调用宿主机的 `gemma4:e4b` 模型。
- Playwright 测试套件通过率 100%。
