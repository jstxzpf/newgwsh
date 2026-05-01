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
