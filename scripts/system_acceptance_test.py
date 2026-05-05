import asyncio
import os
import sys
import subprocess
import time
from playwright.async_api import async_playwright, expect

# 配置区域
BASE_URL = "http://localhost:5173"
USERNAME = "admin"
PASSWORD = "Admin123"
TEST_DOC_TITLE = f"自动测试公文-{int(time.time())}"
TEST_FILE_PATH = os.path.abspath("test_kb_file.txt")

class NBSAcceptanceTester:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        print("\n🚀 [1/7] 启动 Playwright 浏览器...")
        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=False) # 设为 False 以便观察物理测试过程
        self.context = await self.browser.new_context(viewport={'width': 1280, 'height': 800})
        self.page = await self.context.new_page()

    async def login(self):
        print(f"🔐 [2/7] 正在登录系统: {USERNAME}...")
        await self.page.goto(f"{BASE_URL}/login")
        await self.page.fill('input[placeholder="工号"]', USERNAME)
        await self.page.fill('input[placeholder="密码"]', PASSWORD)
        await self.page.click('button:has-text("进入系统")')
        await self.page.wait_for_url(f"{BASE_URL}/dashboard")
        print("✅ 登录成功，进入个人工作台。")

    async def audit_dashboard(self):
        print("📊 [3/7] 正在审计工作台页面元素...")
        # 检查是否还有 Mock 数据（现在应该已经联动真实 API）
        await self.page.wait_for_selector('.ant-statistic-title')
        stats_titles = await self.page.locator('.ant-statistic-title').all_text_contents()
        stats_values = await self.page.locator('.ant-statistic-content-value').all_text_contents()
        
        print(f"📋 检测到指标统计: {dict(zip(stats_titles, stats_values))}")
        
        # 检查水印干扰
        watermark = self.page.locator('div[aria-hidden="true"]')
        if await watermark.count() > 0:
            print("✅ 水印组件已正确应用 aria-hidden=\"true\"，不再干扰无障碍审计。")
        else:
            print("⚠️ 未发现水印或 aria-hidden 属性缺失。")

    async def test_drafting_and_polish(self):
        print(f"📝 [4/7] 测试公文起草与 AI 润色流程...")
        await self.page.click('button:has-text("起草新公文")')
        await self.page.fill('input[placeholder="请输入公文标题"]', TEST_DOC_TITLE)
        
        # 选择第一个文种
        await self.page.click('.ant-select-selector')
        await self.page.click('.ant-select-item-option:has-text("通知")')
        
        await self.page.click('button:has-text("OK")')
        await self.page.wait_for_url(r"**/workspace/.*")
        print(f"📂 已进入工作区: {self.page.url}")

        # 输入正文
        content = "泰兴市2026年统计工作要点包括：加强基层基础建设，提升数据质量。"
        await self.page.fill('textarea[placeholder="在此输入公文正文..."]', content)
        print("✍️ 正文输入完成，准备触发 AI 润色...")

        # 触发润色
        await self.page.click('button:has-text("AI 智能润色")')
        
        # 等待 SSE 通知（根据修复后的逻辑，应弹出成功的 Notification）
        print("⏳ 等待后端 AI 异步任务完成 (通过 SSE 隧道)...")
        try:
            # 等待出现 DIFF 模式特有的元素
            await self.page.wait_for_selector('.diff-mode-container', timeout=30000)
            print("✨ AI 润色完成！页面已自动切入 DIFF 对比模式。")
            
            # 模拟接受建议
            await self.page.click('button:has-text("接受并合并")')
            await self.page.click('button:has-text("确定")') # Popconfirm
            print("✅ 已成功合并 AI 建议。")
        except Exception as e:
            print(f"❌ AI 润色流程超时或失败: {e}")

    async def test_knowledge_upload(self):
        print("📁 [5/7] 测试知识库文件上传与解析流程...")
        await self.page.goto(f"{BASE_URL}/knowledge")
        
        # 触发上传
        async with self.page.expect_file_chooser() as fc_info:
            await self.page.click('button:has-text("上传资产")')
            await self.page.click('.ant-upload-drag')
        
        file_chooser = await fc_info.value
        await file_chooser.set_files(TEST_FILE_PATH)
        
        await self.page.click('button:has-text("开始上传")')
        
        # 等待状态变为 READY
        print("⏳ 等待 Celery Worker 解析文件...")
        try:
            await self.page.wait_for_selector('text=READY', timeout=20000)
            print(f"✅ 文件 {os.path.basename(TEST_FILE_PATH)} 解析成功。")
        except:
            print("⚠️ 文件解析等待超时。")

    async def test_rag_chat(self):
        print("🤖 [6/7] 测试 RAG 穿透式智能问答...")
        await self.page.goto(f"{BASE_URL}/chat")
        
        # 勾选测试文件
        await self.page.check(f'input[type="checkbox"]:near(:text("{os.path.basename(TEST_FILE_PATH)}"))')
        
        # 提问
        query = "2024年泰兴市粮食总产量是多少？"
        await self.page.fill('textarea[placeholder*="统计业务咨询"]', query)
        await self.page.click('button.ant-btn-icon-only') # 发送按钮
        
        print(f"❓ 提问: {query}")
        print("⏳ AI 正在检索并生成回答...")
        
        # 等待回答（根据 test_kb_file.txt 内容，应包含 100万吨）
        try:
            answer_locator = self.page.locator('.ant-typography:has-text("100万吨")')
            await expect(answer_locator).to_be_visible(timeout=30000)
            print("🎯 RAG 测试成功：AI 准确提取到了文档中的事实数据！")
        except Exception as e:
            print(f"❌ RAG 测试失败: 未能在回答中找到预期数据。")

    def show_logs(self):
        print("\n📜 [7/7] 查看系统运行日志 (最近 30 行)...")
        try:
            # 获取 api 和 worker 的日志
            for service in ["api", "worker"]:
                print(f"\n--- {service.upper()} 服务日志 ---")
                result = subprocess.run(
                    ["docker", "compose", "-f", "docker-compose.dev.yml", "logs", "--tail", "30", service],
                    capture_output=True, text=True, encoding="utf-8"
                )
                print(result.stdout if result.stdout else "(无日志输出)")
        except Exception as e:
            print(f"无法获取日志: {e}")

    async def run(self):
        try:
            await self.start()
            await self.login()
            await self.audit_dashboard()
            await self.test_drafting_and_polish()
            await self.test_knowledge_upload()
            await self.test_rag_chat()
            self.show_logs()
        finally:
            if self.browser:
                await self.browser.close()
            print("\n🏁 测试结束。")

if __name__ == "__main__":
    tester = NBSAcceptanceTester()
    asyncio.run(tester.run())
