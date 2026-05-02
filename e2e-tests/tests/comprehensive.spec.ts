import { test, expect } from '@playwright/test';

test.describe('System Comprehensive Physical Test', () => {
  
  test('Full Navigation Test', async ({ page }) => {
    // [Debug] Log request failures
    page.on('requestfailed', request => {
      console.log(`Request failed: ${request.url()} (${request.failure()?.errorText})`);
    });

    // [Debug] Log console messages
    page.on('console', msg => {
      console.log(`PAGE LOG [${msg.type()}]: ${msg.text()}`);
    });

    // 1. 登录
    await page.goto('/login');
    console.log('Login page loaded');
    
    // 截图记录初始状态
    await page.screenshot({ path: 'test-results/login-initial.png' });
    
    await page.fill('input[placeholder="工号 / 用户名"]', 'admin');
    await page.fill('input[placeholder="密码"]', 'Admin123!');
    
    // 点击登录并观察响应
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/auth/login') && resp.status() === 200),
      page.click('button:has-text("登 录")')
    ]);
    
    console.log('Login successful, waiting for auth state persistence...');
    
    // [P0] harden: Explicitly wait for Auth state (token + userInfo) to hit localStorage
    // This prevents race conditions where navigation happens before the store is ready.
    await page.waitForFunction(() => {
      try {
        const storage = localStorage.getItem('taixing-auth-storage');
        if (!storage) return false;
        const state = JSON.parse(storage).state;
        return state && state.token && state.userInfo;
      } catch {
        return false;
      }
    }, { timeout: 15000 });

    console.log('Auth state persistent, entering dashboard...');
    await page.waitForURL(/.*dashboard/, { timeout: 15000 });
    
    // [P0] Stability: Wait for Ant Design layout to appear. 
    // Use .first() to avoid strict mode violation.
    await expect(page.locator('.ant-layout').first()).toBeVisible({ timeout: 15000 });
    
    // Wait for the specific business button to ensure data is loaded
    await expect(page.getByRole('button', { name: /起草新公文/ })).toBeVisible({ timeout: 15000 });

    await page.waitForSelector('#root > *');
    await page.screenshot({ path: 'test-results/dashboard.png' });

    // 2. 检查各页面
    const navItems = [
      { text: '公文中心', url: '/documents', title: '公文管理中心' },
      { text: '知识库', url: '/knowledge', title: '知识资产中心' },
      { text: '智能助手', url: '/chat', title: '智能咨询助手' },
      { text: '任务中心', url: '/tasks', title: '异步任务中心' },
      { text: '签批管控台', url: '/approvals', title: '科长签批管控台' },
      { text: '系统中枢', url: '/settings', title: '系统中枢设置' },
    ];

    for (const item of navItems) {
      console.log(`Testing navigation to ${item.text}...`);
      
      // Use role-based locator for menu item
      await page.getByRole('menuitem', { name: item.text }).click();
      
      // 等待 URL 匹配
      await expect(page).toHaveURL(new RegExp(`.*${item.url}`), { timeout: 10000 });
      
      // [P0] Stability: Wait for React to mount
      await page.waitForSelector('#root > *', { timeout: 10000 });
      // [P0] Stability: Wait for specific title text
      await expect(page.getByText(item.title).first()).toBeVisible({ timeout: 15000 });

      // 检查是否有错误弹出
      const errorMsg = page.locator('.ant-message-error');
      if (await errorMsg.first().isVisible()) {
        const text = await errorMsg.first().innerText();
        console.error(`Error detected on ${item.text}: ${text}`);
      }

      await page.screenshot({ path: `test-results/page-${item.url.slice(1)}.png` });
      }

    // 3. 登出
    console.log('Testing logout...');
    await page.hover('.ant-avatar');
    await page.click('text=退出登录');
    await expect(page).toHaveURL(/.*login/);
  });
});
