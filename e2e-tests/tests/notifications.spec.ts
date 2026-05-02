import { test, expect } from '@playwright/test';

test.describe('Notification System Accuracy and Functionality', () => {
  
  test('Verify unread count and real-time update', async ({ page }) => {
    // 1. 登录
    await page.goto('/login');
    await page.fill('input[placeholder="工号 / 用户名"]', 'admin');
    await page.fill('input[placeholder="密码"]', 'admin123');
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/auth/login') && resp.status() === 200),
      page.click('button:has-text("登 录")')
    ]);

    // 等待进入 Dashboard 并稳定
    await page.waitForURL(/.*dashboard/);
    await page.waitForSelector('#root > *');
    
    // 2. 获取初始通知数 (增加显式等待，因为接口请求是异步的)
    const badge = page.locator('.ant-badge-count');
    
    // [P0] Stability: Wait for a moment for async API to finish
    await page.waitForTimeout(2000); 
    
    let initialCount = 0;
    if (await badge.isVisible()) {
      initialCount = parseInt(await badge.innerText());
      console.log(`Initial unread count: ${initialCount}`);
    } else {
      console.log('Badge not visible, assuming 0');
    }

    // 3. 模拟接收通知 (点击铃铛打开抽屉)
    await page.click('.anticon-bell');
    
    // 验证 Drawer 弹出并等待内容加载
    const drawer = page.locator('.ant-drawer-content');
    await expect(drawer).toBeVisible();
    
    // 4. 验证标记已读功能
    // [P0] harden: Wait for the button to appear in the DOM/UI
    const markReadBtn = page.getByRole('button', { name: '标记已读' }).first();
    
    try {
      await expect(markReadBtn).toBeVisible({ timeout: 5000 });
      console.log('Mark as Read button found, clicking...');
      
      await markReadBtn.click();
      
      // 验证角标减少
      // 注意：0 时 Badge 可能直接消失，需要处理这种情况
      if (initialCount === 1) {
        await expect(badge).not.toBeVisible({ timeout: 5000 });
        console.log('Badge hidden as expected after clearing the last notification');
      } else {
        await page.waitForFunction((prev) => {
          const el = document.querySelector('.ant-badge-count');
          return el && parseInt(el.textContent || '0') < prev;
        }, initialCount, { timeout: 5000 });
        const newCount = parseInt(await badge.innerText());
        console.log(`New unread count: ${newCount}`);
        expect(newCount).toBeLessThan(initialCount);
      }
    } catch (e) {
      console.log('Mark as Read button not visible or badge didn\'t update correctly');
      // If we are here, either there were no unread notifications or the UI is stuck
      if (initialCount === 0) {
        console.log('Skipping click test as initial count was 0');
      } else {
        throw e;
      }
    }

    // 5. 验证后端数据一致性
    const unreadRes = await page.evaluate(async () => {
      const resp = await fetch('/api/v1/notifications/unread-count', {
        headers: { 'Authorization': `Bearer ${JSON.parse(localStorage.getItem('taixing-auth-storage') || '{}').state.token}` }
      });
      return await resp.json();
    });
    
    console.log(`Backend unread count check: ${unreadRes.data.unread_count}`);
    
    // 如果角标显示，它应该与后端一致 (考虑到 0 时 Badge 可能隐藏)
    if (unreadRes.data.unread_count > 0) {
       await expect(badge).toHaveText(unreadRes.data.unread_count.toString());
    } else {
       await expect(badge).not.toBeVisible();
    }
  });
});
