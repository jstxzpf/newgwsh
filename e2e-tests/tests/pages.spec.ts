import { test, expect } from '@playwright/test';

test.describe('System Comprehensive Physical Test', () => {
  
  test.beforeEach(async ({ page }) => {
    // 每次测试前先登录
    await page.goto('/login');
    await page.fill('input[placeholder="工号 / 用户名"]', 'admin');
    await page.fill('input[placeholder="密码"]', 'admin123');
    await page.click('button:has-text("登 录")');
    await expect(page).toHaveURL(/.*dashboard/);
    
    // 检查是否有全局错误消息弹出
    const errorMsg = page.locator('.ant-message-error');
    await expect(errorMsg).not.toBeVisible();
  });

  test('Dashboard page should render correctly', async ({ page }) => {
    await expect(page.locator('text=下午好')).toBeVisible();
    await expect(page.locator('text=最近处理的公文')).toBeVisible();
    await expect(page.locator('text=待我处理')).toBeVisible();
  });

  test('Documents page should render correctly', async ({ page }) => {
    await page.click('text=公文中心');
    await expect(page.locator('text=起草公文')).toBeVisible();
    // 验证 AntD 表格是否出现
    await expect(page.locator('.ant-table')).toBeVisible();
  });

  test('Knowledge Base page should render correctly', async ({ page }) => {
    await page.click('text=知识库');
    await expect(page.locator('text=知识目录')).toBeVisible();
    await expect(page.locator('.ant-tree')).toBeVisible();
  });

  test('AI Assistant page should render correctly', async ({ page }) => {
    await page.click('text=智能助手');
    await expect(page.locator('text=知识挂载范围')).toBeVisible();
    await expect(page.locator('input[placeholder*="问题"]')).toBeVisible();
  });

  test('Tasks page should render correctly', async ({ page }) => {
    await page.click('text=任务中心');
    await expect(page.locator('text=异步任务监控')).toBeVisible();
  });

  test('Approvals page should render correctly', async ({ page }) => {
    await page.click('text=签批管控台');
    await expect(page.locator('text=待我签批')).toBeVisible();
  });

  test('Settings page should render correctly', async ({ page }) => {
    await page.click('text=系统中枢');
    await expect(page.locator('text=系统参数配置')).toBeVisible();
    await expect(page.locator('text=模型引擎状态')).toBeVisible();
  });

  test('Logout should work', async ({ page }) => {
    await page.hover('.ant-avatar');
    await page.click('text=退出登录');
    await expect(page).toHaveURL(/.*login/);
  });
});
