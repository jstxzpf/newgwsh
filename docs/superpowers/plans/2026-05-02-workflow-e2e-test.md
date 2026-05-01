# E2E 测试：完整业务流与 AI 聊天实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 编写并验证 Playwright E2E 测试脚本，模拟完整业务流。

**架构：**
1. 调整前端代码，增加 E2E 测试所需的标识位（h1, class）。
2. 创建 `e2e-tests/tests/workflow.spec.ts`。
3. 验证并提交。

**技术栈：** Playwright, TypeScript, React (Ant Design).

---

### 任务 1：调整前端代码以支持测试

**文件：**
- 修改：`frontend/src/pages/KnowledgeBase.tsx`
- 修改：`frontend/src/pages/Chat.tsx`
- 修改：`frontend/src/components/layout/MainLayout.tsx`

- [ ] **步骤 1：在 KnowledgeBase.tsx 中添加 h1 标题**
- [ ] **步骤 2：在 Chat.tsx 中为 AI 消息添加 .chat-message-ai 类名**
- [ ] **步骤 3：在 MainLayout.tsx 中微调菜单标签以匹配测试脚本**

### 任务 2：创建 E2E 测试脚本

**文件：**
- 创建：`e2e-tests/tests/workflow.spec.ts`

- [ ] **步骤 1：编写测试代码**

```typescript
import { test, expect } from '@playwright/test';

test('full business workflow: knowledge base and AI chat', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[placeholder="用户名"]', 'admin');
  await page.fill('input[placeholder="密码"]', 'admin123');
  await page.click('button:has-text("登录")');

  await expect(page).toHaveURL(/.*dashboard/);

  await page.click('text=知识库');
  await expect(page.locator('h1')).toContainText('知识库管理');

  await page.click('text=智能助手');
  await page.fill('input[placeholder*="统计咨询问题"]', '你好，gemma');
  await page.press('input[placeholder*="统计咨询问题"]', 'Enter');
  
  const response = page.locator('.chat-message-ai');
  await expect(response).toBeVisible({ timeout: 30000 });
});
```

### 任务 3：提交与验证

- [ ] **步骤 1：提交代码**
- [ ] **步骤 2：确认 DONE**
