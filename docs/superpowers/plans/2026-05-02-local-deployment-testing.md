# 本地部署与物理测试程序实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 通过 Docker Compose 一键部署系统，并创建完整的 Playwright E2E 测试套件验证系统功能。

**架构：** 
- **部署**：使用 Docker Compose 启动 DB, Redis, API, Worker。
- **AI**：后端连接宿主机 Ollama (`gemma4:e4b`)。
- **测试**：在 `e2e-tests` 目录使用 Playwright (TypeScript) 进行自动化测试。

**技术栈：** Docker Compose, Playwright, TypeScript, Ollama.

---

### 任务 1：配置本地环境与 Docker 网络

**文件：**
- 修改：`.env`
- 修改：`docker-compose.yml`

- [ ] **步骤 1：更新 .env 配置**
确保 `OLLAMA_BASE_URL` 指向宿主机（Windows 宿主机在 Docker 中通常为 `host.docker.internal`）。
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e4b
```

- [ ] **步骤 2：在 docker-compose.yml 中添加 host.docker.internal 映射**
在 `api` 和 `worker` 服务中添加 `extra_hosts`。
```yaml
services:
  api:
    extra_hosts:
      - "host.docker.internal:host-gateway"
  worker:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

- [ ] **步骤 3：启动 Docker Compose**
运行：`docker-compose up -d`
预期：所有容器启动并显示为 Healthy。

- [ ] **步骤 4：Commit**
```bash
git add .env docker-compose.yml
git commit -m "deploy: configure local docker network for ollama"
```

---

### 任务 2：初始化 Playwright 测试环境

**文件：**
- 创建：`e2e-tests/package.json`
- 创建：`e2e-tests/playwright.config.ts`

- [ ] **步骤 1：创建 e2e-tests 目录并初始化 package.json**
```bash
mkdir e2e-tests
cd e2e-tests
npm init -y
npm install -D @playwright/test typescript
```

- [ ] **步骤 2：编写 playwright.config.ts**
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173', // 假设前端 dev server 在此端口
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

- [ ] **步骤 3：Commit**
```bash
git add e2e-tests/package.json e2e-tests/playwright.config.ts
git commit -m "test: initialize playwright environment"
```

---

### 任务 3：编写基础功能与认证测试

**文件：**
- 创建：`e2e-tests/tests/auth.spec.ts`

- [ ] **步骤 1：编写认证测试代码**
```typescript
import { test, expect } from '@playwright/test';

test('login page renders correctly', async ({ page }) => {
  await page.goto('/login');
  await expect(page).toHaveTitle(/Login/);
  await expect(page.getByPlaceholder('用户名')).toBeVisible();
});

test('successful login redirects to dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[placeholder="用户名"]', 'admin');
  await page.fill('input[placeholder="密码"]', 'admin123');
  await page.click('button:has-text("登录")');
  await expect(page).toHaveURL(/.*dashboard/);
});
```

- [ ] **步骤 2：运行测试验证**
运行：`npx playwright test tests/auth.spec.ts`
预期：测试通过。

- [ ] **步骤 3：Commit**
```bash
git add e2e-tests/tests/auth.spec.ts
git commit -m "test: add auth e2e tests"
```

---

### 任务 4：模拟 AI 聊天与完整业务流

**文件：**
- 创建：`e2e-tests/tests/workflow.spec.ts`

- [ ] **步骤 1：编写完整业务流测试**
模拟登录 -> 知识库上传 -> AI 聊天。
```typescript
import { test, expect } from '@playwright/test';

test('full business workflow: knowledge base and AI chat', async ({ page }) => {
  // 1. 登录
  await page.goto('/login');
  await page.fill('input[placeholder="用户名"]', 'admin');
  await page.fill('input[placeholder="密码"]', 'admin123');
  await page.click('button:has-text("登录")');

  // 2. 进入知识库并检查页面内容
  await page.click('text=知识库');
  await expect(page.locator('h1')).toContainText('知识库管理');

  // 3. 进入 AI 聊天并发送消息
  await page.click('text=智能助手');
  await page.fill('textarea', '你好，gemma');
  await page.press('textarea', 'Enter');
  
  // 等待 AI 响应
  const response = page.locator('.chat-message-ai');
  await expect(response).toBeVisible({ timeout: 30000 });
});
```

- [ ] **步骤 2：运行全量测试**
运行：`npx playwright test`
预期：所有测试通过。

- [ ] **步骤 3：Commit**
```bash
git add e2e-tests/tests/workflow.spec.ts
git commit -m "test: add full workflow e2e tests"
```
