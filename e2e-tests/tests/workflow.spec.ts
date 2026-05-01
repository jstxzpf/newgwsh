import { test, expect } from '@playwright/test';

test('full business workflow: knowledge base and AI chat', async ({ page }) => {
  // 1. 登录
  await page.goto('/login');
  await page.fill('input[placeholder="用户名"]', 'admin');
  await page.fill('input[placeholder="密码"]', 'admin123');
  await page.click('button:has-text("登录")');

  // 验证登录成功跳转
  await expect(page).toHaveURL(/.*dashboard/);

  // 2. 进入知识库
  await page.click('text=知识库');
  await expect(page.locator('h1')).toContainText('知识库管理');

  // 3. 进入智能助手（智能问答）
  await page.click('text=智能助手');
  
  // 4. 发送 AI 聊天消息
  const chatInput = page.locator('input[placeholder*="统计咨询问题"]');
  await chatInput.fill('你好，gemma');
  await chatInput.press('Enter');
  
  // 5. 等待 AI 响应
  const response = page.locator('.chat-message-ai');
  await expect(response).toBeVisible({ timeout: 30000 });
  await expect(response).toContainText(/泰兴/);
});
