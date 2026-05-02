import { test, expect } from '@playwright/test';

test('login page renders correctly', async ({ page }) => {
  await page.goto('/login');
  // 匹配实际的 document title
  await expect(page).toHaveTitle(/国家统计局泰兴调查队公文处理系统/);
  // 匹配 AntD 的 placeholder
  await expect(page.getByPlaceholder('工号 / 用户名')).toBeVisible();
});

test('successful login redirects to dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[placeholder="工号 / 用户名"]', 'admin');
  await page.fill('input[placeholder="密码"]', 'Admin123!');
  
  // 打印控制台日志
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  
  await Promise.all([
    page.waitForResponse(resp => resp.url().includes('/auth/login')),
    page.click('button:has-text("登 录")')
  ]);
  
  await expect(page).toHaveURL(/.*dashboard/);
});
