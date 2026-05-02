import { test, expect } from '@playwright/test';

test.describe('System Comprehensive Function Test', () => {

  test.beforeEach(async ({ page }) => {
    // 登录系统
    await page.goto('/login');
    await page.fill('input[placeholder="工号 / 用户名"]', 'admin');
    await page.fill('input[placeholder="密码"]', 'admin123');
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/auth/login')),
      page.click('button:has-text("登 录")')
    ]);
    // 等待跳转并确保菜单可见
    await expect(page.locator('text=个人工作台')).toBeVisible();
  });

  test('Dashboard -> Document Flow', async ({ page }) => {
    await page.click('button:has-text("起草新公文")');
    await expect(page).toHaveURL(/.*documents/);
    
    await page.click('button:has-text("起草新公文")');
    const modal = page.locator('.ant-modal');
    await expect(modal).toBeVisible();
    await expect(modal.locator('text=请选择公文文种:')).toBeVisible();
    
    // 按 Esc 键关闭弹窗
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible();
  });

  test('Knowledge Base interactions', async ({ page }) => {
    await page.click('text=知识库');
    await page.click('div.ant-tabs-tab-btn:has-text("科室共享库")');
    await expect(page.locator('button:has-text("上传文件 / 文件夹")')).toBeVisible();
    await page.click('div.ant-tabs-tab-btn:has-text("参考范文")');
    await expect(page.locator('text=范文标题')).toBeVisible();
  });

  test('Settings interactions', async ({ page }) => {
    await page.click('text=系统中枢');
    await page.click('div.ant-tabs-tab-btn:has-text("系统参数")');
    await expect(page.locator('label[title="编辑锁 TTL (秒)"]')).toBeVisible();
    await expect(page.locator('button:has-text("保存配置")')).toBeVisible();

    await page.click('div.ant-tabs-tab-btn:has-text("健康监控")');
    // 修复冲突选择器
    await expect(page.locator('.ant-statistic-title:has-text("AI 引擎")')).toBeVisible();

    await page.click('div.ant-tabs-tab-btn:has-text("提示词管理")');
    await expect(page.locator('text=system_chat.txt')).toBeVisible();
  });

  test('Approvals interactions', async ({ page }) => {
    await page.click('text=签批管控台');
    
    // 验证有"审阅", "批准", "驳回" 按钮（如果有数据的话）
    // 列表里有Mock数据，所以应该能看到
    await expect(page.locator('text=泰兴调查队安全生产工作通知')).toBeVisible();
    await expect(page.locator('button:has-text("审阅")')).toBeVisible();
    await expect(page.locator('button:has-text("批准")')).toBeVisible();
    await expect(page.locator('button:has-text("驳回")')).toBeVisible();
  });

  test('Tasks interactions', async ({ page }) => {
    await page.click('text=任务中心');
    
    // 验证任务列表中的按钮
    await expect(page.locator('button:has-text("终止")').first()).toBeVisible();
    await expect(page.locator('button:has-text("日志")').first()).toBeVisible();
  });
});
