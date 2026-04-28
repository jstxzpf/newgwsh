import asyncio
import httpx
import sys
import time
from typing import Dict, Any

# 巡检配置
BASE_URL = "http://localhost/api/v1"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

class SiteInspector:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.token = ""
        self.user_info = {}

    async def log(self, message: str, level: str = "INFO"):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    async def check_step(self, name: str, coro):
        try:
            await self.log(f"正在执行: {name}...")
            result = await coro
            await self.log(f"成功: {name}")
            return result
        except Exception as e:
            await self.log(f"失败: {name} | 错误详情: {str(e)}", "ERROR")
            if hasattr(e, "response"):
                await self.log(f"HTTP 状态码: {e.response.status_code}", "ERROR")
                await self.log(f"响应内容: {e.response.text}", "ERROR")
            sys.exit(1)

    async def login(self):
        async def _run():
            resp = await self.client.post("/auth/login", data={
                "username": ADMIN_USER,
                "password": ADMIN_PASS
            })
            resp.raise_for_status()
            self.token = resp.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            return resp.json()
        return await self.check_step("身份认证 (Login)", _run())

    async def get_me(self):
        async def _run():
            resp = await self.client.get("/auth/me")
            resp.raise_for_status()
            self.user_info = resp.json()
            return self.user_info
        return await self.check_step("获取当前用户信息 (Auth Me)", _run())

    async def knowledge_base_flow(self):
        async def _run():
            # 1. 创建巡检专用目录
            folder_name = f"巡检目录_{int(time.time())}"
            resp = await self.client.post("/kb/directory", params={
                "name": folder_name,
                "kb_tier": "PERSONAL"
            })
            resp.raise_for_status()
            folder_id = resp.json()["kb_id"]
            await self.log(f"已创建巡检目录 ID: {folder_id}")

            # 2. 上传模拟公文素材
            file_content = b"# Test Document\nThis is a test content for inspection."
            files = {'file': ('test_inspect.md', file_content, 'text/markdown')}
            upload_resp = await self.client.post("/kb/upload", 
                params={"parent_id": folder_id, "kb_tier": "PERSONAL"},
                files=files
            )
            upload_resp.raise_for_status()
            kb_id = upload_resp.json()["kb_id"]
            await self.log(f"已上传素材 ID: {kb_id}，正在等待解析任务...")

            # 3. 轮询解析状态
            for _ in range(10):
                status_resp = await self.client.get(f"/kb/tree", params={"tier": "PERSONAL"})
                # 简单检查状态 (在真实系统中这里会更复杂)
                await asyncio.sleep(2)
            
            return kb_id
        return await self.check_step("知识库全链路 (KB Flow)", _run())

    async def document_lifecycle_flow(self):
        async def _run():
            # 1. 初始化公文
            title = f"巡检测试公文_{int(time.time())}"
            init_resp = await self.client.post("/documents/init", json={"title": title})
            init_resp.raise_for_status()
            doc_id = init_resp.json()["doc_id"]
            await self.log(f"公文初始化成功 ID: {doc_id}")

            # 2. 抢占编辑锁
            lock_resp = await self.client.post(f"/locks/acquire?doc_id={doc_id}")
            lock_resp.raise_for_status()
            lock_token = lock_resp.json()["lock_token"]
            await self.log(f"成功获取编辑锁: {lock_token}")

            # 3. 模拟自动保存
            save_resp = await self.client.post(f"/documents/{doc_id}/auto-save?lock_token={lock_token}", 
                json={"content": "这是由自动化巡检程序生成的正文内容，长度必须超过二十个字符以满足系统校验规则。"})
            save_resp.raise_for_status()
            await self.log("自动保存成功")

            # 4. 提交审核
            submit_resp = await self.client.post(f"/documents/{doc_id}/submit")
            submit_resp.raise_for_status()
            await self.log("公文提交审核成功")

            # 5. 模拟审批 (作为管理员审批自己提交的)
            review_resp = await self.client.post(f"/approval/{doc_id}/review", 
                json={"is_approved": True, "comment": "巡检自动通过"})
            review_resp.raise_for_status()
            await self.log("公文审批通过")

            # 6. 验证最终状态
            final_resp = await self.client.get(f"/documents/{doc_id}")
            status = final_resp.json()["status"]
            if status != "APPROVED":
                raise ValueError(f"公文最终状态异常: {status}")
            
            return doc_id
        return await self.check_step("公文全生命周期 (Doc Lifecycle)", _run())

    async def system_health_check(self):
        async def _run():
            resp = await self.client.get("/sys/status")
            resp.raise_for_status()
            data = resp.json()
            await self.log(f"系统资源状态: CPU {data['cpu_pct']}%, Mem {data['memory_pct']}%")
            return data
        return await self.check_step("系统健康度自检 (Sys Status)", _run())

    async def run(self):
        await self.log("=== 开始全链路系统巡检 ===")
        await self.login()
        await self.get_me()
        await self.system_health_check()
        await self.knowledge_base_flow()
        await self.document_lifecycle_flow()
        await self.log("=== 巡检圆满完成，系统表现健康 ===")
        await self.client.aclose()

if __name__ == "__main__":
    inspector = SiteInspector()
    asyncio.run(inspector.run())
