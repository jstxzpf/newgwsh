#!python
# -*- coding: utf-8 -*-
"""
泰兴调查队公文处理系统 V3.0 — 系统管理演示程序
================================================
用于模拟系统管理员向观众演示整个系统运行过程。

用法:
  python scripts/admin_demo.py                    # 交互模式 + Chrome 浏览器
  python scripts/admin_demo.py --no-browser       # 纯 API 模式（无浏览器）
  python scripts/admin_demo.py --no-pause         # 自动播放模式
  python scripts/admin_demo.py --phase 3          # 仅演示指定阶段
  python scripts/admin_demo.py --phase 3-6        # 演示阶段 3-6
  python scripts/admin_demo.py --screenshots      # 关键步骤截图
  python scripts/admin_demo.py --slow-mo 500      # 浏览器操作速度 (ms)
"""

import asyncio
import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.syntax import Syntax
from rich.rule import Rule
from rich.text import Text
from rich.columns import Columns
from rich.box import Box, ROUNDED, HEAVY, DOUBLE
from rich.style import Style
from rich.align import Align

# ════════════════════════════════════════════════════════════════
# 配置
# ════════════════════════════════════════════════════════════════
API_BASE = os.environ.get("DEMO_API_BASE", "http://localhost:8000/api/v1")
FRONTEND_BASE = os.environ.get("DEMO_FRONTEND_BASE", "http://localhost:5173")
ADMIN_USER = os.environ.get("DEMO_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("DEMO_ADMIN_PASS", "Admin123")

USERS = {
    "admin":       {"un": "admin",      "pw": "Admin123",    "lvl": 99, "dept": "OFFICE",        "name": "系统管理员"},
    "kz_nongye":   {"un": "kz_nongye",  "pw": "Password123", "lvl": 5,  "dept": "AGRICULTURE",  "name": "王农业"},
    "ky_nongye":   {"un": "ky_nongye",  "pw": "Password123", "lvl": 1,  "dept": "AGRICULTURE",  "name": "李小农"},
    "kz_zhuhu":    {"un": "kz_zhuhu",   "pw": "Password123", "lvl": 5,  "dept": "HOUSEHOLD",    "name": "张住户"},
}

ROLE_BADGES = {
    99: "[white on red] 管理员 [/]",
    5:  "[white on yellow] 科长 [/]",
    1:  "[white on green] 科员 [/]",
}

DOC_TYPES = {
    1: ("NOTICE",        "通知"),
    2: ("REQUEST",       "请示"),
    3: ("RESEARCH",      "调研分析"),
    4: ("ECONOMIC_INFO", "经济信息"),
    5: ("GENERAL",       "通用文档"),
}

NODE_LABELS = {
    10: "起草", 11: "快照", 20: "AI润色请求", 21: "AI润色应用",
    30: "提交审批", 40: "签批通过", 41: "驳回", 42: "回退修改",
    99: "强制释放锁",
}

# ════════════════════════════════════════════════════════════════
# 主类
# ════════════════════════════════════════════════════════════════
class AdminDemo:
    def __init__(self, auto_mode: bool = False, no_browser: bool = False,
                 screenshots: bool = False, slow_mo: int = 300):
        self.console = Console()
        self.auto_mode = auto_mode
        self.no_browser = no_browser
        self.screenshots = screenshots
        self.slow_mo = slow_mo
        self.api_token: Optional[str] = None
        self.user_tokens: Dict[str, str] = {}
        self.created_doc_ids: List[str] = []
        self.stats = {"api_calls": 0, "start_time": None, "errors": 0}
        self._step_count = 0
        # Playwright state
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
        self._screenshot_idx = 0

    # ════════════════════════════════════════════════════════════
    # 浏览器生命周期
    # ════════════════════════════════════════════════════════════
    async def _start_browser(self):
        if self.no_browser:
            return
        self.console.print("\n  [dim]正在启动 Chrome 浏览器...[/]")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            slow_mo=self.slow_mo,
            args=["--start-maximized"]
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="zh-CN"
        )
        if self.screenshots:
            os.makedirs(self._screenshot_dir, exist_ok=True)
        self._page = await self._context.new_page()
        self.console.print("  [green]└─ Chrome 浏览器已启动[/]")

    async def _stop_browser(self):
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        finally:
            self._page = None
            self._context = None
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self.console.print("  [dim]浏览器已关闭[/]")

    async def _screenshot(self, label: str):
        if not self.screenshots or not self._page:
            return
        self._screenshot_idx += 1
        fname = f"step_{self._screenshot_idx:03d}_{label}.png"
        fpath = os.path.join(self._screenshot_dir, fname)
        await self._page.screenshot(path=fpath, full_page=True)
        self.console.print(f"  [dim]📸 截图: {fname}[/]")

    # ════════════════════════════════════════════════════════════
    # 浏览器 UI 操作辅助
    # ════════════════════════════════════════════════════════════
    async def _ui_step(self, label: str, action=None):
        """执行浏览器操作步骤，带 Rich 输出。action 为可调用对象 (lambda)"""
        self._step_count += 1
        sn = f"{self._step_count:02d}"
        self.console.print(f"\n  [bold cyan]┌─ Step {sn}: {label} 🌐[/]")
        if self.no_browser or not self._page or action is None:
            self.console.print("  [dim]│ (无浏览器模式，跳过)[/]")
            self.console.print(f"  [dim]└─ 已跳过[/]")
            return
        try:
            await action()
            self.console.print(f"  [bold green]└─ 完成 ✓[/]")
            await self._screenshot(label)
        except Exception as e:
            self.console.print(f"  [bold yellow]└─ 浏览器操作异常: {e}[/]")
            self.stats["errors"] += 1

    async def _ui_login(self, username: str, password: str):
        """浏览器登录"""
        if self.no_browser or not self._page:
            return
        await self._page.goto(f"{FRONTEND_BASE}/login", wait_until="networkidle")
        await self._page.fill('input[id="username"]', username)
        await self._page.fill('input[id="password"]', password)
        await self._page.click('button[type="submit"]')
        await self._page.wait_for_url("**/dashboard", timeout=10000)
        self.console.print("  [green]  └─ 浏览器登录成功，已跳转仪表盘[/]")

    async def _ui_nav(self, menu_label: str):
        """侧边栏导航到指定菜单"""
        if self.no_browser or not self._page:
            return
        # Click the antd menu item by its text
        await self._page.click(f'li.ant-menu-item:has-text("{menu_label}")')
        await self._page.wait_for_timeout(500)

    async def _ui_click_btn(self, text: str):
        """按文本点击按钮"""
        if self.no_browser or not self._page:
            return
        await self._page.click(f'button:has-text("{text}")')
        await self._page.wait_for_timeout(300)

    async def _ui_fill_field(self, placeholder: str, value: str):
        """按 placeholder 填写表单字段"""
        if self.no_browser or not self._page:
            return
        await self._page.fill(f'input[placeholder*="{placeholder}"]', value)
        await self._page.wait_for_timeout(200)

    async def _ui_select(self, placeholder: str, option_text: str):
        """选择下拉框选项"""
        if self.no_browser or not self._page:
            return
        await self._page.click(f'.ant-select:has-text("{placeholder}")')
        await self._page.wait_for_timeout(300)
        await self._page.click(f'.ant-select-item-option:has-text("{option_text}")')
        await self._page.wait_for_timeout(200)

    async def _ui_create_document(self, title: str, doc_type: str):
        """浏览器: 仪表盘创建新公文"""
        if self.no_browser or not self._page:
            return
        # 确保在仪表盘页面
        if "dashboard" not in self._page.url:
            await self._ui_nav("个人工作台")
        await self._page.wait_for_timeout(500)
        # 点击"起草新公文"按钮
        await self._page.click('button:has-text("起草新公文")')
        await self._page.wait_for_timeout(500)
        # 填写标题
        await self._page.fill('input[placeholder*="请输入公文标题"]', title)
        # 选择文种
        await self._page.click('.ant-select')
        await self._page.wait_for_timeout(300)
        await self._page.click(f'.ant-select-item-option:has-text("{doc_type}")')
        await self._page.wait_for_timeout(200)
        # 点击确定
        await self._page.click('button:has-text("OK")')
        await self._page.wait_for_timeout(1000)

    # ════════════════════════════════════════════════════════════
    # API 层
    # ════════════════════════════════════════════════════════════
    async def _api(self, method: str, path: str, json_data=None, data=None,
                   files=None, token=None, log: bool = True) -> dict:
        t = token or self.api_token
        headers = {}
        if t:
            headers["Authorization"] = f"Bearer {t}"
        url = f"{API_BASE}{path}"
        self.stats["api_calls"] += 1
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers, params=data)
                elif method == "POST":
                    if files:
                        resp = await client.post(url, data=data, files=files, headers=headers)
                    else:
                        resp = await client.post(url, json=json_data, headers=headers)
                elif method == "PUT":
                    resp = await client.put(url, json=json_data, headers=headers)
                elif method == "DELETE":
                    resp = await client.delete(url, headers=headers)
                else:
                    return {"status": 0, "body": {}, "error": f"Unknown method: {method}"}
                body = resp.json() if resp.text else {}
                return {"status": resp.status_code, "body": body}
        except Exception as e:
            return {"status": 0, "body": {}, "error": str(e)}

    async def _api_step(self, label: str, method: str, path: str, **kw) -> dict:
        self._step_count += 1
        sn = f"{self._step_count:02d}"
        self.console.print(f"\n  [bold magenta]┌─ Step {sn}: {label}[/]")
        self.console.print(f"  [dim]│ {method} {path}[/]")
        res = await self._api(method, path, **kw)
        status = res.get("status", 0)
        if status == 0:
            self.console.print(f"  [bold red]└─ FAIL[/] 网络错误: {res.get('error', 'unknown')}")
            self.stats["errors"] += 1
        elif 200 <= status < 300:
            self.console.print(f"  [bold green]└─ HTTP {status} ✓[/]")
        else:
            self.console.print(f"  [bold yellow]└─ HTTP {status} ⚠[/]")
            if res.get("body", {}).get("message"):
                self.console.print(f"     [dim]{res['body'].get('message')}[/]")
        return res

    async def _login_as(self, user_key: str) -> Optional[str]:
        if user_key in self.user_tokens:
            return self.user_tokens[user_key]
        u = USERS.get(user_key)
        if not u:
            return None
        res = await self._api("POST", "/auth/login",
            json_data={"username": u["un"], "password": u["pw"]}, log=False)
        token = res.get("body", {}).get("data", {}).get("access_token")
        if token:
            self.user_tokens[user_key] = token
        return token

    # ════════════════════════════════════════════════════════════
    # 输出辅助
    # ════════════════════════════════════════════════════════════
    def _title(self, text: str):
        self.console.print()
        self.console.print(Rule(style="gold1"))
        self.console.print(Align.center(Text(text, style="bold gold1")))
        self.console.print(Rule(style="gold1"))

    def _phase(self, num: int, title: str):
        self.console.print()
        self.console.print(Panel(
            Align.center(Text(f"第 {num} 阶段\n{title}", style="bold cyan")),
            border_style="cyan", box=DOUBLE, padding=(1, 3)
        ))

    def _info(self, text: str):
        self.console.print(Panel(text, border_style="blue", padding=(0, 1)))

    def _show_json(self, res: dict, title: str = "响应"):
        body = res.get("body", {})
        if not body:
            return
        data = body.get("data", body)
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        if len(json_str) > 600:
            json_str = json_str[:600] + "\n  ... (已截断)"
        self.console.print(Panel(
            Syntax(json_str, "json", theme="monokai", word_wrap=True),
            title=f"[bold cyan]{title}[/]",
            border_style="green" if res.get("status", 0) < 400 else "red",
            padding=(0, 1)
        ))

    def _table(self, title: str, columns: list, rows: list):
        t = Table(title=f"[bold cyan]{title}[/]", box=ROUNDED, header_style="bold cyan")
        for c in columns:
            t.add_column(c, no_wrap=len(columns) <= 4)
        for row in rows:
            t.add_row(*[str(x) for x in row])
        self.console.print(t)

    def _state_flow(self, states: list, current: str):
        """渲染状态机流程图"""
        arrows = []
        for s in states:
            if s == current:
                arrows.append(f"[bold green]{s}[/]")
            else:
                arrows.append(f"[dim]{s}[/]")
        self.console.print("  " + " [bold cyan]→[/] ".join(arrows))

    def _wait(self, msg: str = "按 Enter 继续..."):
        if self.auto_mode:
            self.console.print(f"\n[dim]⏳ {msg} (自动模式, 2s)[/]")
            time.sleep(2)
        else:
            self.console.print(f"\n[dim]⏎ {msg}[/]", end="")
            input()

    def _role_badge(self, lvl: int) -> str:
        return ROLE_BADGES.get(lvl, f"[white on blue] Lv.{lvl} [/]")

    # ════════════════════════════════════════════════════════════
    # 第1阶段: 系统启动与认证
    # ════════════════════════════════════════════════════════════
    async def phase_01_startup(self):
        self._phase(1, "系统启动与身份认证")
        self._info("演示管理员登录（浏览器 + API）、JWT 令牌获取、系统健康检查、身份解析及安全拦截。")

        # 1.1 浏览器登录演示
        await self._ui_step("浏览器打开登录页 → 填写工号/密码 → 登录",
            lambda: self._ui_login(ADMIN_USER, ADMIN_PASS))
        self._wait()

        # 1.2 API 登录获取 JWT
        res = await self._api_step("管理员登录获取 JWT 令牌", "POST", "/auth/login",
            json_data={"username": ADMIN_USER, "password": ADMIN_PASS})
        self.api_token = res.get("body", {}).get("data", {}).get("access_token")
        if self.api_token:
            self.console.print("  [green]  └─ Token: {}...{}[/]".format(
                self.api_token[:30], self.api_token[-15:]))
        self._wait()

        # 1.3 系统健康探针 (需要认证)
        res = await self._api_step("系统健康探针 (DB/Redis/AI)", "GET", "/sys/status")
        if res.get("status") == 200:
            d = res["body"].get("data", {})
            rows = [
                ("PostgreSQL",   "✓ 正常" if d.get("db_connected")       else "✗ 异常"),
                ("Redis",        "✓ 正常" if d.get("redis_connected")    else "✗ 异常"),
                ("AI 引擎",      "✓ 在线" if d.get("ai_engine_online")   else "✗ 离线"),
                ("Celery 工作节点", str(d.get("celery_workers_active", "?"))),
            ]
            self._table("系统健康状态", ["组件", "状态"], rows)
        self._wait()

        # 1.4 身份解析
        res = await self._api_step("JWT 令牌解析 - 获取当前用户", "GET", "/auth/me")
        if res.get("status") == 200:
            u = res["body"].get("data", {})
            rows = [
                ("用户ID",   str(u.get("user_id", "?"))),
                ("用户名",   u.get("username", "?")),
                ("姓名",     u.get("full_name", "?")),
                ("角色等级", str(u.get("role_level", "?"))),
                ("所属科室", u.get("department_name", "?")),
                ("科室负责人", "是" if u.get("is_dept_head") else "否"),
            ]
            self._table("当前登录用户", ["属性", "值"], rows)
        self._wait()

        # 1.5 系统配置
        res = await self._api_step("系统配置参数一览", "GET", "/sys/config")
        if res.get("status") == 200:
            configs = res["body"].get("data", [])
            if configs:
                self._table("系统配置", ["Key", "Value", "Description"],
                    [(c["key"], c["value"], c.get("description", "")) for c in configs])
        self._wait()

        # 1.6 错误密码
        res = await self._api_step("安全: 错误密码拒绝 (HTTP 401)", "POST", "/auth/login",
            json_data={"username": ADMIN_USER, "password": "wrong_password"})
        if res.get("status") == 401:
            self.console.print("  [green]  └─ 正确拦截：用户名或密码错误[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第2阶段: 组织架构管理
    # ════════════════════════════════════════════════════════════
    async def phase_02_organization(self):
        self._phase(2, "组织架构与基础数据")
        self._info("浏览系统内的科室设置、用户账户、公文文种等基础配置。")

        # 2.0 浏览器导航到系统中枢设置
        await self._ui_step("浏览器: 侧边栏 → [系统中枢设置] 查看管理界面",
            lambda: self._ui_nav("系统中枢设置"))
        self._wait()

        # 2.1 科室列表
        res = await self._api_step("科室列表查询", "GET", "/sys/departments")
        if res.get("status") == 200:
            depts = res["body"].get("data", [])
            self._table(f"系统科室 ({len(depts)} 个)", ["ID", "科室名称", "编码", "负责人ID", "状态"],
                [(d["dept_id"], d["dept_name"], d["dept_code"],
                  d.get("dept_head_id", ""), "启用" if d.get("is_active") else "停用")
                 for d in depts])
        self._wait()

        # 2.2 用户列表
        res = await self._api_step("用户列表查询", "GET", "/sys/users")
        if res.get("status") == 200:
            users = res["body"].get("data", [])
            self._table(f"系统用户 ({len(users)} 人)", ["ID", "用户名", "姓名", "角色等级", "科室", "状态"],
                [(u["user_id"], u["username"], u.get("full_name",""),
                  f"{u.get('role_level',0)} {self._role_badge(u.get('role_level',0))}",
                  u.get("dept_id",""), "启用" if u.get("is_active") else "停用")
                 for u in users])
        self._wait()

        # 2.3 文种类型
        res = await self._api_step("公文文种类型列表", "GET", "/sys/doc-types")
        if res.get("status") == 200:
            types = res["body"].get("data", [])
            self._table(f"公文文种 ({len(types)} 种)", ["ID", "编码", "名称", "状态"],
                [(t["type_id"], t["type_code"], t["type_name"],
                  "启用" if t.get("is_active") else "停用") for t in types])
        self._wait()

        # 2.4 组织架构概览
        self.console.print(Panel(
            "   [bold]办公室[/] (OFFICE)\n"
            "   ├── [bold red]admin[/] — 系统管理员 (Lv.99)\n\n"
            "   [bold]农业调查科[/] (AGRICULTURE)\n"
            "   ├── [bold yellow]kz_nongye[/] — 王农业 科长 (Lv.5)\n"
            "   └── [bold green]ky_nongye[/] — 李小农 科员 (Lv.1)\n\n"
            "   [bold]住户调查科[/] (HOUSEHOLD)\n"
            "   └── [bold yellow]kz_zhuhu[/] — 张住户 科长 (Lv.5)",
            title="[bold cyan]组织架构树[/]", border_style="blue", padding=(1, 2)
        ))
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第3阶段: 公文全生命周期
    # ════════════════════════════════════════════════════════════
    async def phase_03_documents(self):
        self._phase(3, "公文全生命周期")
        self._info(
            "演示公文从起草到归档的完整流转过程：\n"
            "  DRAFTING → SUBMITTED → REVIEWED → APPROVED → ARCHIVED\n"
            "以及驳回+回退的异常路径。"
        )

        states_display = ["DRAFTING", "SUBMITTED", "REVIEWED", "APPROVED", "ARCHIVED"]

        # 3.1 起草公文
        ts = int(time.time())
        # 浏览器演示：导航到仪表盘 → 点击起草 → 填写表单
        await self._ui_step("浏览器: 仪表盘 → 点击[起草新公文] → 填写标题/文种 → 确认",
            lambda: self._ui_create_document(f"演示公文-{ts}", "通知"))
        res = await self._api_step("起草新公文 (POST /documents/init)", "POST", "/documents/init",
            json_data={"title": f"演示公文-{ts}", "doc_type_id": 1})
        doc_id = res.get("body", {}).get("data", {}).get("doc_id")
        if doc_id:
            self.created_doc_ids.append(doc_id)
            self.console.print(f"  [green]  └─ 公文ID: [bold cyan]{doc_id}[/][/]")
            self._state_flow(states_display, "DRAFTING")
        else:
            self.console.print("  [red]  └─ 创建失败，后续公文步骤将跳过[/]")
            self._wait()
            return
        self._wait()

        # 3.2 查看详情
        res = await self._api_step("查看公文详情 (初始状态)", "GET", f"/documents/{doc_id}")
        if res.get("status") == 200:
            d = res["body"].get("data", {})
            self._table("公文详情", ["字段", "值"], [
                ("标题", d.get("title", "?")),
                ("状态", f"[bold]{d.get('status', '?')}[/]"),
                ("文种", d.get("doc_type_name", "?")),
                ("创建者", d.get("creator_name", "?")),
                ("创建时间", d.get("created_at", "?")),
            ])
        self._wait()

        # 3.3 自动保存
        content = "泰兴调查队2025年一季度统计调查工作取得阶段性成效。全队完成住户调查1200户、农业调查45个样本村，数据质量合格率99.2%。"
        res = await self._api_step("自动保存草稿内容", "POST", f"/documents/{doc_id}/auto-save",
            json_data={"title": f"演示公文-{ts}", "content": content})
        self._wait()

        # 3.4 快照列表
        res = await self._api_step("快照列表查询", "GET", f"/documents/{doc_id}/snapshots")
        if res.get("status") == 200:
            snaps = res["body"].get("data", {}).get("items", [])
            self.console.print(f"  [dim]  快照数量: {len(snaps)}[/]")
        self._wait()

        # 3.5 提交审批
        res = await self._api_step("提交审批 (DRAFTING → SUBMITTED)", "POST",
            f"/documents/{doc_id}/submit")
        if res.get("status") == 200:
            self._state_flow(states_display, "SUBMITTED")
        self._wait()

        # 3.6 验证 SUBMITTED
        res = await self._api_step("验证状态: SUBMITTED", "GET", f"/documents/{doc_id}")
        s = res.get("body", {}).get("data", {}).get("status", "?")
        self.console.print(f"  [green]  当前状态: {s}[/]")
        self._wait()

        # 3.7 科长审核
        kz_token = await self._login_as("kz_nongye")
        res = await self._api_step("科长审核通过 (SUBMITTED → REVIEWED)", "POST",
            f"/approval/{doc_id}/review",
            json_data={"action": "APPROVE", "comments": "内容翔实，同意上报签发。"},
            token=kz_token)
        if res.get("status") == 200:
            self._state_flow(states_display, "REVIEWED")
        self._wait()

        # 3.8 验证 REVIEWED
        res = await self._api_step("验证状态: REVIEWED", "GET", f"/documents/{doc_id}")
        s = res.get("body", {}).get("data", {}).get("status", "?")
        self.console.print(f"  [green]  当前状态: {s}[/]")
        self._wait()

        # 3.9 局长签发
        res = await self._api_step("局长签发 (REVIEWED → APPROVED)", "POST",
            f"/approval/{doc_id}/issue")
        if res.get("status") == 200:
            d = res["body"].get("data", {})
            doc_number = d.get("document_number", "未生成")
            self._state_flow(states_display, "APPROVED")
            self.console.print(f"  [green]  └─ 发文编号: [bold gold1]{doc_number}[/][/]")
        self._wait()

        # 3.10 验证 APPROVED
        res = await self._api_step("验证状态: APPROVED (终态)", "GET", f"/documents/{doc_id}")
        s = res.get("body", {}).get("data", {}).get("status", "?")
        self.console.print(f"  [green]  当前状态: {s}[/]")
        self._wait()

        # 3.11 归档
        res = await self._api_step("归档公文 (APPROVED → ARCHIVED)", "POST",
            f"/documents/{doc_id}/archive")
        if res.get("status") == 200:
            self._state_flow(states_display + ["ARCHIVED"], "ARCHIVED")
        self._wait()

        # 3.12 SIP 存证
        res = await self._api_step("SIP 存证完整性校验", "GET",
            f"/documents/{doc_id}/verify-sip")
        if res.get("status") == 200:
            d = res["body"].get("data", {})
            match = d.get("match", False)
            if match:
                self.console.print(f"  [green]  └─ SIP 存证校验: 通过 ✓[/]")
            else:
                self.console.print(f"  [yellow]  └─ SIP 存证校验: {d.get('reason', '未通过')} ⚠[/]")
        self._wait()

        # 3.13-3.15 驳回+回退
        self.console.print("\n  [bold cyan]┈┈┈ 异常路径演示: 驳回 → 回退修改 ┈┈┈[/]")
        ts2 = int(time.time())
        res2 = await self._api("POST", "/documents/init",
            json_data={"title": f"驳回演示-{ts2}", "doc_type_id": 2})
        doc_id2 = res2.get("body", {}).get("data", {}).get("doc_id")
        if doc_id2:
            self.created_doc_ids.append(doc_id2)
            await self._api("POST", f"/documents/{doc_id2}/submit")
            self.console.print(f"  [dim]  创建第二份公文: {doc_id2} 并提交[/]")

            res = await self._api_step("科长驳回 (SUBMITTED → REJECTED)", "POST",
                f"/approval/{doc_id2}/review",
                json_data={"action": "REJECT", "comments": "需补充数据来源说明。"},
                token=kz_token)
            if res.get("status") == 200:
                self.console.print("  [green]  └─ 已驳回，理由: 需补充数据来源说明。[/]")
            self._wait()

            res = await self._api_step("回退修改 (REJECTED → DRAFTING)", "POST",
                f"/documents/{doc_id2}/revise")
            if res.get("status") == 200:
                ns = res["body"].get("data", {}).get("new_status", "?")
                self.console.print(f"  [green]  └─ 已回退，新状态: {ns}[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第4阶段: 分布式编辑锁
    # ════════════════════════════════════════════════════════════
    async def phase_04_locks(self):
        self._phase(4, "分布式编辑锁机制")
        self._info("演示编辑锁的获取、心跳续期、冲突检测、释放及管理员强拆功能。")

        # 创建测试文档
        ts = int(time.time())
        res = await self._api("POST", "/documents/init",
            json_data={"title": f"锁演示-{ts}", "doc_type_id": 1})
        doc_id = res.get("body", {}).get("data", {}).get("doc_id")
        if doc_id:
            self.created_doc_ids.append(doc_id)

        # 4.1 获取锁
        res = await self._api_step("获取编辑锁 (POST /locks/acquire)", "POST", "/locks/acquire",
            json_data={"doc_id": doc_id})
        lock_token = res.get("body", {}).get("data", {}).get("lock_token")
        ttl = res.get("body", {}).get("data", {}).get("ttl", "?")
        if lock_token:
            self.console.print(f"  [green]  └─ Lock Token: {lock_token[:20]}... TTL: {ttl}s[/]")
        self._wait()

        # 4.2 跨用户冲突
        ky_token = await self._login_as("ky_nongye")
        res = await self._api_step("跨用户锁冲突检测 (HTTP 423)", "POST", "/locks/acquire",
            json_data={"doc_id": doc_id}, token=ky_token)
        if res.get("status") == 423:
            self.console.print("  [green]  └─ 正确拒绝：锁已被其他用户持有[/]")
        self._wait()

        # 4.3 心跳
        if lock_token:
            res = await self._api_step("心跳续期 (POST /locks/heartbeat)", "POST",
                "/locks/heartbeat", json_data={"doc_id": doc_id, "lock_token": lock_token})
            if res.get("status") == 200:
                nxt = res["body"].get("data", {}).get("next_suggested_heartbeat", "?")
                self.console.print(f"  [green]  └─ 下次建议心跳: {nxt}s 后[/]")
        self._wait()

        # 4.4 查看活跃锁
        res = await self._api_step("查看系统活跃锁列表", "GET", "/sys/locks")
        if res.get("status") == 200:
            locks = res["body"].get("data", [])
            if locks:
                self._table("活跃锁", ["文档ID", "持有者", "Token前缀"],
                    [(l.get("doc_id",""), l.get("holder",""), l.get("token","")[:15]+"...") for l in locks])
            else:
                self.console.print("  [dim]  当前无活跃锁[/]")
        self._wait()

        # 4.5 释放锁
        if lock_token:
            res = await self._api_step("释放编辑锁", "POST", "/locks/release",
                json_data={"doc_id": doc_id, "lock_token": lock_token})
        self._wait()

        # 4.6 锁配置
        res = await self._api_step("锁配置参数查询", "GET", "/locks/config")
        if res.get("status") == 200:
            d = res["body"].get("data", {})
            self._table("锁配置", ["参数", "值"], [
                ("Lock TTL", f"{d.get('lock_ttl_seconds', '?')} 秒"),
                ("心跳间隔", f"{d.get('heartbeat_interval_seconds', '?')} 秒"),
            ])
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第5阶段: 知识库管理
    # ════════════════════════════════════════════════════════════
    async def phase_05_knowledge(self):
        self._phase(5, "知识库资产管理")
        self._info("演示知识库层级结构、版本快照、文件上传解析及跨科室权限隔离。")

        # 5.0 浏览器导航到知识库
        await self._ui_step("浏览器: 侧边栏 → [统计知识资产] 查看知识库界面",
            lambda: self._ui_nav("统计知识资产"))
        self._wait()

        # 5.1 BASE 层级
        res = await self._api_step("知识库 BASE 层级查询", "GET", "/kb/hierarchy?tier=BASE")
        if res.get("status") == 200:
            items = res["body"].get("data", [])
            self._table(f"BASE 知识库 ({len(items)} 条)", ["ID", "名称", "类型", "安全级别", "状态"],
                [(i.get("kb_id",""), i.get("kb_name",""), i.get("kb_type",""),
                  i.get("security_level",""), i.get("parse_status","")) for i in items[:10]])
        self._wait()

        # 5.2 版本快照
        res = await self._api_step("知识库快照版本", "GET", "/kb/snapshot-version")
        if res.get("status") == 200:
            ver = res["body"].get("data", {}).get("snapshot_version", "?")
            self.console.print(f"  [green]  └─ 当前快照版本: [bold]{ver}[/][/]")
        self._wait()

        # 5.3 文件上传
        res = await self._api_step("上传文件到个人知识库", "POST", "/kb/upload",
            data={"kb_tier": "PERSONAL", "security_level": "GENERAL"},
            files={"file": ("demo_upload.txt", "泰兴调查队演示文件内容。".encode(), "text/plain")})
        if res.get("status") == 200:
            kb_id = res["body"].get("data", {}).get("kb_id") or res["body"].get("data", {}).get("node_id", "?")
            self.console.print(f"  [green]  └─ 上传成功, KB ID: {kb_id}[/]")
        self._wait()

        # 5.4 PERSONAL 层级
        res = await self._api_step("个人知识库层级查询", "GET", "/kb/hierarchy?tier=PERSONAL")
        if res.get("status") == 200:
            items = res["body"].get("data", [])
            self.console.print(f"  [dim]  PERSONAL 层级共 {len(items)} 条[/]")
        self._wait()

        # 5.5 跨科室隔离
        self.console.print("\n  [bold cyan]┈┈┈ 跨科室权限隔离验证 ┈┈┈[/]")
        ky_token = await self._login_as("ky_nongye")
        zh_token = await self._login_as("kz_zhuhu")

        # 用 ky_nongye 上传 DEPT 文件
        await self._api("POST", "/kb/upload",
            data={"kb_tier": "DEPT", "security_level": "GENERAL"},
            files={"file": ("agriculture_dept.txt", "农业调查科内部文件。".encode(), "text/plain")},
            token=ky_token, log=False)

        # kz_zhuhu 查 DEPT
        res = await self._api_step("跨科室隔离: 住户科看不到农业科文件", "GET",
            "/kb/hierarchy?tier=DEPT", token=zh_token)
        if res.get("status") == 200:
            items = res["body"].get("data", [])
            dept_files = [i.get("kb_name","") for i in items]
            self.console.print(f"  [green]  └─ kz_zhuhu (住户科) 可见 {len(items)} 条科室文件[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第6阶段: AI 智能问答
    # ════════════════════════════════════════════════════════════
    async def phase_06_ai_chat(self):
        self._phase(6, "AI 智能问答 (RAG)")
        self._info("演示基于知识库的 RAG 智能问答，SSE 流式响应和防幻觉降级机制。")

        # 6.0 浏览器导航到智能问答
        await self._ui_step("浏览器: 侧边栏 → [智能穿透问答] 查看 AI 对话界面",
            lambda: self._ui_nav("智能穿透问答"))
        self._wait()

        # 6.1 流式问答
        self._step_count += 1
        sn = f"{self._step_count:02d}"
        self.console.print(f"\n  [bold magenta]┌─ Step {sn}: SSE 流式问答[/]")
        self.console.print(f"  [dim]│ POST /chat/stream[/]")
        self.console.print(f"  [dim]│ Query: 2025年泰兴调查队统计工作成果[/]")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {"Authorization": f"Bearer {self.api_token}"}
                async with client.stream("POST", f"{API_BASE}/chat/stream",
                    json={"query": "2025年泰兴调查队统计工作取得了哪些成果？", "context_kb_ids": []},
                    headers=headers) as resp:
                    if resp.status_code == 200:
                        self.console.print("  [green]└─ HTTP 200 (text/event-stream) ✓[/]")
                        chunks = []
                        with Live(Text(""), console=self.console, refresh_per_second=6, transient=False) as live:
                            async for line in resp.aiter_lines():
                                if line.startswith("data:"):
                                    chunks.append(line)
                                    display = "\n".join(chunks[-8:])
                                    live.update(Panel(display[:500], title="[bold green]AI 实时回复[/]",
                                        border_style="green", padding=(0, 1)))
                        self.console.print(f"  [dim]  收到 {len(chunks)} 个 SSE 数据块[/]")
                    else:
                        body = await resp.aread()
                        self.console.print(f"  [yellow]└─ HTTP {resp.status_code} ⚠ {body[:100]}[/]")
        except Exception as e:
            self.console.print(f"  [yellow]  └─ 流式连接失败: {e} (可能 AI 引擎未就绪)[/]")
        self._wait()

        # 6.2 空上下文降级
        self._step_count += 1
        sn = f"{self._step_count:02d}"
        self.console.print(f"\n  [bold magenta]┌─ Step {sn}: 空上下文防幻觉降级[/]")
        self.console.print(f"  [dim]│ POST /chat/stream (空 context)[/]")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {"Authorization": f"Bearer {self.api_token}"}
                async with client.stream("POST", f"{API_BASE}/chat/stream",
                    json={"query": "请生成一份随机的统计报告", "context_kb_ids": []},
                    headers=headers) as resp:
                    full = ""
                    async for line in resp.aiter_lines():
                        full += line + "\n"
                    fallback = "未探明对应统计线索" in full or "无法" in full
                    self.console.print(
                        f"  [{'green' if fallback else 'yellow'}]"
                        f"  └─ 防幻觉降级: {'已触发 ✓' if fallback else '未触发 ⚠'}[/]")
        except Exception as e:
            self.console.print(f"  [yellow]  └─ 请求失败: {e}[/]")
        self._wait()

        # 6.3 SSE 票据
        res = await self._api_step("SSE 票据发放", "POST", "/sse/ticket",
            json_data={"task_id": "user_events"})
        if res.get("status") == 200:
            ticket = res["body"].get("data", {}).get("ticket", "?")
            self.console.print(f"  [green]  └─ 票据: {ticket[:30]}...[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第7阶段: 参考范文库
    # ════════════════════════════════════════════════════════════
    async def phase_07_exemplars(self):
        self._phase(7, "参考范文库")
        self._info("演示范文库按文种过滤、内容预览及上传权限控制。")

        # 7.1 范文列表
        res = await self._api_step("范文列表 (按文种过滤)", "GET", "/exemplars?doc_type_id=1")
        if res.get("status") == 200:
            exs = res["body"].get("data", [])
            self._table(f"范文列表 ({len(exs)} 篇)", ["ID", "标题", "文种", "层级", "时间"],
                [(e.get("exemplar_id",""), e.get("title",""), e.get("doc_type_id",""),
                  e.get("tier",""), e.get("created_at","")) for e in exs[:10]])
        self._wait()

        # 7.2 范文预览
        res = await self._api_step("范文内容预览", "GET", "/exemplars/1/preview")
        if res.get("status") == 200:
            content = res["body"].get("data", {}).get("content", "")
            if content:
                self.console.print(Panel(content[:300], title="范文预览 (前300字)",
                    border_style="green", padding=(0, 1)))
            else:
                self.console.print("  [dim]  无范文内容[/]")
        self._wait()

        # 7.3 权限验证
        ky_token = await self._login_as("ky_nongye")
        res = await self._api_step("科员无权上传范文 (HTTP 403)", "POST", "/exemplars/upload",
            data={"title": "test", "doc_type_id": "1"},
            files={"file": ("test.docx", b"fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            token=ky_token)
        if res.get("status") == 403:
            self.console.print("  [green]  └─ 权限拦截正确 ✓[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第8阶段: 异步任务管理
    # ════════════════════════════════════════════════════════════
    async def phase_08_tasks(self):
        self._phase(8, "异步任务与 SSE 通知")
        self._info("演示异步任务（润色/排版）的派发、状态查询、重试机制。")

        # 8.1 任务列表
        res = await self._api_step("任务列表查询", "GET", "/tasks")
        if res.get("status") == 200:
            tasks = res["body"].get("data", {}).get("items", [])
            if tasks:
                self._table(f"异步任务 ({len(tasks)} 条)", ["ID", "类型", "状态", "进度", "文档"],
                    [(t.get("task_id","")[:12]+"...", t.get("task_type",""),
                      t.get("task_status",""), f"{t.get('progress_pct',0)}%",
                      t.get("doc_id","")[:12]+"...") for t in tasks[:10]])
            else:
                self.console.print("  [dim]  当前无任务记录[/]")
        self._wait()

        # 8.2 触发润色
        if self.created_doc_ids:
            doc_id = self.created_doc_ids[0]
            res = await self._api_step(f"触发 AI 润色任务", "POST", "/tasks/polish",
                json_data={"doc_id": doc_id, "context_kb_ids": [], "exemplar_id": None})
            if res.get("status") == 202:
                task_id = res["body"].get("data", {}).get("task_id", "?")
                self.console.print(f"  [green]  └─ 任务已接受, Task ID: {task_id[:20]}...[/]")
        self._wait()

        # 8.3 排版任务
        if self.created_doc_ids:
            doc_id = self.created_doc_ids[0]
            res = await self._api_step("触发排版任务 (docx 生成)", "POST", "/tasks/format",
                json_data={"doc_id": doc_id})
            if res.get("status") == 202:
                task_id = res["body"].get("data", {}).get("task_id", "?")
                self.console.print(f"  [green]  └─ 排版任务已派发, Task ID: {task_id[:20]}...[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第9阶段: 通知与审计
    # ════════════════════════════════════════════════════════════
    async def phase_09_notifications_audit(self):
        self._phase(9, "消息通知与安全审计")
        self._info("演示用户通知中心、未读消息统计和安全审计日志查询。")

        # 9.1 通知列表
        res = await self._api_step("通知列表查询", "GET", "/notifications")
        if res.get("status") == 200:
            notifs = res["body"].get("data", {}).get("items", [])
            self._table(f"通知中心 ({len(notifs)} 条)", ["ID", "类型", "内容", "已读"],
                [(n.get("notification_id",""), n.get("type",""), (n.get("content","") or "")[:30],
                  "✓" if n.get("is_read") else "[bold]未读[/]") for n in notifs[:10]])
        self._wait()

        # 9.2 未读数
        res = await self._api_step("未读通知统计", "GET", "/notifications/unread-count")
        if res.get("status") == 200:
            count = res["body"].get("data", {}).get("unread_count", 0)
            self.console.print(f"  [green]  └─ 未读通知: [bold]{count}[/] 条[/]")
        self._wait()

        # 9.3 审计日志
        res = await self._api_step("安全审计日志全览", "GET", "/audit")
        if res.get("status") == 200:
            logs = res["body"].get("data", {}).get("items", [])
            self._table(f"审计日志 ({len(logs)} 条)", ["ID", "公文ID", "节点", "操作者", "时间"],
                [(l.get("audit_id",""), (l.get("doc_id","") or "-")[:12],
                  NODE_LABELS.get(l.get("node_id"), f"#{l.get('node_id')}"),
                  l.get("operator_id",""), (l.get("timestamp","") or "")[:19])
                 for l in logs[:10]])
        self._wait()

        # 9.4 分页查询
        res = await self._api_step("审计日志分页查询", "GET", "/audit?page=1&page_size=5")
        if res.get("status") == 200:
            total = res["body"].get("data", {}).get("total", 0)
            self.console.print(f"  [green]  └─ 审计日志总数: [bold]{total}[/] 条[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第10阶段: 系统维护与提示词
    # ════════════════════════════════════════════════════════════
    async def phase_10_maintenance(self):
        self._phase(10, "系统维护与提示词管理")
        self._info("演示提示词文件管理、锁监控大盘、仪表盘统计、缓存清理和数据快照。")

        # 10.0 浏览器导航到系统中枢设置
        await self._ui_step("浏览器: 侧边栏 → [系统中枢设置] 查看维护面板",
            lambda: self._ui_nav("系统中枢设置"))
        self._wait()

        # 10.1 提示词列表
        res = await self._api_step("提示词文件列表", "GET", "/sys/prompts")
        if res.get("status") == 200:
            prompts = res["body"].get("data", [])
            self._table("提示词文件", ["文件名"], [[p["filename"]] for p in prompts])
        self._wait()

        # 10.2 锁监控大盘
        res = await self._api_step("锁监控大盘", "GET", "/sys/locks")
        if res.get("status") == 200:
            locks = res["body"].get("data", [])
            self.console.print(f"  [green]  └─ 当前活跃锁: [bold]{len(locks)}[/] 个[/]")
        self._wait()

        # 10.3 仪表盘统计
        res = await self._api_step("仪表盘公文统计", "GET", "/documents/dashboard/stats")
        if res.get("status") == 200:
            d = res["body"].get("data", {})
            self._table("公文统计", ["状态", "数量"], [
                ("草稿 (DRAFTING)",   d.get("drafted", 0)),
                ("已提交 (SUBMITTED)", d.get("submitted", 0)),
                ("已审核 (REVIEWED)",  d.get("reviewed", 0)),
                ("已驳回 (REJECTED)",  d.get("rejected", 0)),
                ("已签发 (APPROVED)",  d.get("approved", 0)),
                ("已归档 (ARCHIVED)",  d.get("archived", 0)),
            ])
        self._wait()

        # 10.4 缓存清理
        res = await self._api_step("系统缓存清理", "POST", "/sys/cleanup-cache")
        if res.get("status") == 200:
            cleaned = res["body"].get("data", {}).get("cleaned_files", 0)
            self.console.print(f"  [green]  └─ 已清理 [bold]{cleaned}[/] 个临时文件[/]")
        self._wait()

        # 10.5 数据库快照
        res = await self._api_step("数据库快照列表", "GET", "/sys/db-snapshots")
        if res.get("status") == 200:
            snaps = res["body"].get("data", [])
            self.console.print(f"  [green]  └─ 快照数量: [bold]{len(snaps)}[/] 个[/]")
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 第11阶段: 权限矩阵演示
    # ════════════════════════════════════════════════════════════
    async def phase_11_permissions(self):
        self._phase(11, "三级权限隔离矩阵验证")
        self._info("分别以管理员、科长、科员身份登录，验证数据可见性和操作权限边界。")

        matrix = [
            # (label, user_key, method, path, body, expect)
            ("管理员-全量文档可见",         "admin",      "GET",  "/documents?page_size=5", None, 200),
            ("科长(农业)-本科室文档",       "kz_nongye",  "GET",  "/documents?page_size=5", None, 200),
            ("科员(农业)-本人+已提交文档",   "ky_nongye",  "GET",  "/documents?page_size=5", None, 200),
            ("科员-无权查看审计日志",        "ky_nongye",  "GET",  "/audit",                 None, 403),
            ("科员-无权签批公文",            "ky_nongye",  "POST", "/approval/fake/review",  {"action":"APPROVE","comments":"test"}, 403),
            ("科长-可查看任务列表",          "kz_nongye",  "GET",  "/tasks",                 None, 200),
            ("住户科长-看不到农业科文档",    "kz_zhuhu",   "GET",  "/documents?page_size=5", None, 200),
        ]

        results = []
        for label, user_key, method, path, body, expect in matrix:
            u = USERS[user_key]
            token = await self._login_as(user_key)
            if not token:
                results.append((label, u["name"] + self._role_badge(u["lvl"]), expect, "N/A", "登录失败"))
                continue

            res = await self._api(method, path, json_data=body, token=token, log=False)
            actual = res.get("status", 0)
            ok = actual == expect
            icon = "[green]✓[/]" if ok else "[yellow]⚠[/]"
            badge = u["name"] + " " + self._role_badge(u["lvl"])
            results.append((label, badge, expect, actual, icon))

        self._step_count += 1
        sn = f"{self._step_count:02d}"
        self.console.print(f"\n  [bold magenta]┌─ Step {sn}: 权限矩阵验证[/]")
        self._table("权限矩阵", ["测试场景", "角色", "预期", "实际", "结果"], results)
        self._wait()

    # ════════════════════════════════════════════════════════════
    # 主入口
    # ════════════════════════════════════════════════════════════
    async def run(self, phases: Optional[List[int]] = None):
        self.stats["start_time"] = time.time()

        # ═══ 开场 ═══
        self.console.print()
        self.console.print(Rule(style="bold gold1"))
        self.console.print(Align.center(Text("泰兴调查队公文处理系统 V3.0", style="bold gold1")))
        self.console.print(Align.center(Text("国家统计局泰兴调查队 — 系统管理演示程序", style="dim")))
        self.console.print(Rule(style="bold gold1"))
        self.console.print()
        self.console.print(f"  API 基址:    [cyan]{API_BASE}[/]")
        self.console.print(f"  前端基址:    [cyan]{FRONTEND_BASE}[/]")
        self.console.print(f"  管理员:      [cyan]{ADMIN_USER}[/]")
        browser_mode = "Chrome 浏览器可视化" if not self.no_browser else "纯 API (无浏览器)"
        self.console.print(f"  模式:     [cyan]{'自动播放' if self.auto_mode else '交互演示 (按 Enter 推进)'}[/]")
        self.console.print(f"  浏览器:   [cyan]{browser_mode}[/]")
        if not self.no_browser:
            self.console.print(f"  操作速度: [cyan]{self.slow_mo}ms[/]")
            if self.screenshots:
                self.console.print(f"  截图:     [cyan]已启用 ({self._screenshot_dir})[/]")
        self._wait("按 Enter 开始系统演示...")

        # 启动浏览器
        await self._start_browser()

        all_phases = {
            1:  ("系统启动与认证",       self.phase_01_startup),
            2:  ("组织架构管理",         self.phase_02_organization),
            3:  ("公文全生命周期",       self.phase_03_documents),
            4:  ("分布式编辑锁",         self.phase_04_locks),
            5:  ("知识库资产管理",       self.phase_05_knowledge),
            6:  ("AI 智能问答",          self.phase_06_ai_chat),
            7:  ("参考范文库",           self.phase_07_exemplars),
            8:  ("异步任务管理",         self.phase_08_tasks),
            9:  ("通知与审计",           self.phase_09_notifications_audit),
            10: ("系统维护与提示词",     self.phase_10_maintenance),
            11: ("权限矩阵验证",         self.phase_11_permissions),
        }

        if phases is None:
            phases = list(all_phases.keys())

        try:
            for phase_num in phases:
                if phase_num not in all_phases:
                    continue
                name, method = all_phases[phase_num]
                try:
                    await method()
                except Exception as e:
                    self.console.print(f"\n  [bold red]阶段 {phase_num} ({name}) 异常: {e}[/]")
                    self.stats["errors"] += 1
                if phase_num != phases[-1]:
                    self._wait(f"第 {phase_num} 阶段完成，按 Enter 继续...")
        finally:
            # 确保浏览器总是关闭
            await self._stop_browser()

        # ═══ 终场 ═══
        elapsed = time.time() - self.stats["start_time"]

        self.console.print()
        self.console.print(Rule(style="bold gold1"))
        self.console.print(Align.center(Text("演示结束", style="bold gold1")))
        self.console.print(Rule(style="bold gold1"))

        self._table("演示统计", ["指标", "值"], [
            ("API 调用次数",  str(self.stats["api_calls"])),
            ("总耗时",        f"{elapsed:.1f} 秒"),
            ("异常数",        str(self.stats["errors"])),
        ])

        if self.created_doc_ids:
            self.console.print(f"\n  [dim]本次演示创建了 {len(self.created_doc_ids)} 份测试公文[/]")

        self.console.print(f"\n  [bold green]✅ 全系统演示完成！[/]")


# ════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════
def main():
    global API_BASE
    _default_api = API_BASE

    parser = argparse.ArgumentParser(description="泰兴调查队公文处理系统 V3.0 管理演示程序")
    parser.add_argument("--no-pause", action="store_true", help="自动播放模式，无需手动按 Enter")
    parser.add_argument("--no-browser", action="store_true", help="纯 API 模式（不启动浏览器）")
    parser.add_argument("--screenshots", action="store_true", help="关键步骤截图保存到 screenshots/")
    parser.add_argument("--slow-mo", type=int, default=300, help="浏览器操作速度（毫秒，默认 300）")
    parser.add_argument("--phase", type=str, help="仅运行指定阶段 (e.g., 1, 3, 1-5, 3-8)")
    parser.add_argument("--api-base", type=str, default=_default_api, help="API 基址")
    args = parser.parse_args()

    API_BASE = args.api_base

    # 解析阶段范围
    phases = None
    if args.phase:
        phases = set()
        for part in args.phase.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                phases.update(range(int(start), int(end) + 1))
            else:
                phases.add(int(part))
        phases = sorted(phases)

    demo = AdminDemo(
        auto_mode=args.no_pause,
        no_browser=args.no_browser,
        screenshots=args.screenshots,
        slow_mo=args.slow_mo
    )
    asyncio.run(demo.run(phases))


if __name__ == "__main__":
    main()
