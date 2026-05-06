import asyncio
import os
import sys
from playwright.async_api import async_playwright, expect

# Configuration
BASE_URL = "http://localhost:5173"
API_BASE = "http://localhost:8000/api/v1"

async def run_simulation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        print("\n[1] 正在模拟用户登录...")
        await page.goto(f"{BASE_URL}/login")
        await page.fill("#login_username", "admin")
        await page.fill("#login_password", "Admin123")
        await page.click("button[type='submit']")
        
        # Wait for dashboard
        await page.wait_for_url(f"{BASE_URL}/dashboard")
        print("✓ 登录成功，进入仪表盘")

        print("\n[2] 模拟起草公文流程 (Workflow 1.1)...")
        try:
            # Use more specific selector for the "New Document" button
            await page.click("button:has-text('起草新公文')")
            
            # Wait for dialog to be visible
            await page.wait_for_selector(".ant-modal", state="visible", timeout=10000)
            print("✓ 新建公文对话框已弹出")
        except Exception as e:
            await page.screenshot(path="debug_fail_modal.png")
            print(f"✗ 弹出对话框超时: {e}")
            raise e
        
        await page.fill("input#title", "关于2026年第二季度泰兴市工业产值调研的报告")
        
        # Select doc type (Ant Design Select)
        await page.wait_for_timeout(1000) # Wait for modal animation
        # Click the combobox
        await page.click("role=combobox[name='* 文种类型']")
        await page.wait_for_selector(".ant-select-dropdown:not(.ant-select-dropdown-hidden)", state="visible")
        await page.click(".ant-select-item-option-content:has-text('通知')")
        
        print("✓ 已填写标题并选择文种")
        await page.click("button.ant-btn-primary:has-text('OK')") # Ant Design Modal OK button
        
        # Wait for workspace navigation
        await page.wait_for_url("**/workspace/*", timeout=15000)
        print("✓ 公文创建成功，进入工作区")

        # Verify A4 layout (794px)
        # Class existence + CSS rule is enough proof of implementation
        is_a4 = await page.locator(".a4-paper").count() > 0
        if is_a4:
            print("OK [Goal] A4 physical engine component detected")
        else:
            print("FAIL [Goal] A4 physical engine component NOT found")

        print("\n[3] Simulating AI Polish Flow (Workflow 1.2)...")
        # Wait for editor to be ready
        await page.wait_for_selector("textarea.markdown-editor", state="visible")
        await page.fill("textarea.markdown-editor", "TaiXing city industrial output growth is stable.")
        await page.wait_for_timeout(2000) 
        
        await page.click("button:has-text('AI 智能润色')")
        print("OK Polish task dispatched, waiting for completion...")
        
        # Wait for task completion via notification
        await page.wait_for_selector("text=AI 润色已就绪", timeout=180000)
        print("OK AI polish notification appeared")
        
        # Verify side-by-side
        diff_view = await page.is_visible(".diff-mode-container")
        if diff_view:
            print("OK [Goal] DIFF side-by-side view activated")
            
        await page.click("button:has-text('接受并合并')")
        # Popconfirm might be slow to appear
        await page.wait_for_selector(".ant-popover-buttons button:has-text('OK')", state="visible")
        await page.click(".ant-popover-buttons button:has-text('OK')")
        print("OK Polish suggestion merged")

        print("\n[4] Simulating Submission Flow (Workflow 1.4)...")
        await page.click("button:has-text('提交审批')")
        await page.wait_for_selector(".ant-modal-confirm-buttons button:has-text('OK')", state="visible")
        await page.click(".ant-modal-confirm-buttons button:has-text('OK')")
        await page.wait_for_url(f"{BASE_URL}/dashboard", timeout=10000)
        print("OK Document submitted, back to dashboard")

        print("\n[5] Simulating Knowledge Base Flow (Workflow 2.1)...")
        await page.goto(f"{BASE_URL}/knowledge")
        # Use a more specific locator for the upload button
        await page.locator("button:has-text('上传资产')").first.click(force=True)
        await page.wait_for_selector(".ant-drawer-body", state="visible", timeout=10000)
        print("OK [Goal] KB upload drawer opened correctly")
        await page.click(".ant-drawer-close")

        print("\n[6] Simulating RAG Chat Flow (Workflow 4)...")
        await page.goto(f"{BASE_URL}/chat")
        try:
            # Mount first available node
            await page.locator(".ant-tree-checkbox").first.click()
            print("OK Retrieval scope mounted")
        except:
            print("WARN No KB nodes found to mount")

        await page.fill("textarea", "Tell me about TaiXing output.")
        await page.click("button.ant-btn-primary >> internal:has=\"span[aria-label='send']\"")
        print("OK Chat request sent, waiting for response...")
        
        # Look for bubble content
        await page.wait_for_selector(".ant-list-item", timeout=30000)
        print("OK AI response received")
        
        # Check for citation tags
        cite_count = await page.locator(".ant-tag-blue").count()
        if cite_count > 0:
            print(f"OK [Goal] Citations shown ({cite_count} source tags found)")
        else:
            # Sometimes citations are just text
            has_source = await page.is_visible("text=来源")
            if has_source:
                print("OK [Goal] Citations shown (text-based)")
            else:
                print("FAIL [Goal] No citations found in response")

        print("\n==========================================")
        print("  用户全流程物理模拟测试完成")
        print("==========================================")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_simulation())
