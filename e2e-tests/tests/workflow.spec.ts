import { test, expect } from '@playwright/test';

test('full business workflow: knowledge base and AI chat', async ({ page }) => {
  // 1. 登录
  await page.goto('/login');
  await page.fill('input[placeholder="工号 / 用户名"]', 'admin');
  await page.fill('input[placeholder="密码"]', 'Admin123!');
  await page.click('button:has-text("登 录")');

  // 验证登录成功跳转
  await expect(page).toHaveURL(/.*dashboard/);

  // 2. 进入知识库
  await page.click('text=知识库');
  await expect(page.locator('h1, h2, h3, h4')).toContainText('知识资产中心');

  // 3. 进入智能助手
  await page.click('text=智能助手');
  
  // 4. 发送 AI 聊天消息
  // 查阅 Chat.tsx 发现输入框是 Input，placeholder 可能包含“输入统计咨询问题”
  const chatInput = page.locator('input[placeholder*="问题"]');
  await chatInput.fill('你好，gemma');
  await chatInput.press('Enter');
  
  // 5. 等待 AI 响应
  const response = page.locator('.chat-message-ai').last();
  await expect(response).toBeVisible({ timeout: 60000 });
});
