# 认证 E2E 测试实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `e2e-tests` 目录下编写并配置登录认证的 Playwright E2E 测试。

**架构：** 使用 Playwright 框架在 `e2e-tests/tests` 目录下创建 `auth.spec.ts`，包含登录页面渲染和成功登录跳转的测试用例。

**技术栈：** Playwright, TypeScript

---

### 任务 1：创建认证测试文件

**文件：**
- 创建：`e2e-tests/tests/auth.spec.ts`

- [ ] **步骤 1：编写测试代码**

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

- [ ] **步骤 2：验证文件创建成功**

运行：`ls e2e-tests/tests/auth.spec.ts`
预期：文件存在且内容正确。

- [ ] **步骤 3：提交更改**

运行：
```bash
git add e2e-tests/tests/auth.spec.ts
git commit -m "test: add auth e2e tests"
```
预期：提交成功。
