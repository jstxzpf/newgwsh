import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:5173/login');
  
  await page.fill('input[placeholder="工号 / 用户名"]', 'admin');
  await page.fill('input[placeholder="密码"]', 'Admin123!');
  
  await Promise.all([
    page.waitForNavigation(),
    page.click('button[type="submit"]')
  ]);
  
  console.log('Current URL:', page.url());
  const content = await page.textContent('body');
  if (content.includes('个人工作台') || content.includes('Dashboard')) {
    console.log('Login successful');
  } else {
    console.log('Login failed');
    await page.screenshot({ path: 'login_fail.png' });
  }
  
  await browser.close();
})();
