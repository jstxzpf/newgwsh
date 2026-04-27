import pytest
import uuid
import json
import asyncio
from app.models.user import User
from app.api.dependencies import get_current_user
from app.main import app
from app.core.redis import get_redis

@pytest.fixture
def auth_override():
    """权限覆盖 Fixture，确保测试后清理依赖注入状态"""
    yield app.dependency_overrides
    app.dependency_overrides.clear()

@pytest.fixture
async def redis_client():
    """提供 Redis 客户端 Fixture"""
    client = await get_redis()
    yield client
    # 清理测试数据可以使用 flushdb，但为了安全建议只删除测试相关的 key
    # 这里保持简单，由测试用例自行负责

@pytest.mark.asyncio
async def test_sse_security_isolation(client, auth_override, redis_client):
    """
    TC-02 SSE 安全边界集成测试
    1. 测试权限控制 (P0)
    2. 测试 Ticket 阅后即焚 (P0)
    3. 测试无效 Ticket
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    user_a = User(user_id=101, username="UserA", role_level=1)
    user_b = User(user_id=102, username="UserB", role_level=1)
    
    # 1. 准备工作：在 Redis 中预设任务归属关系
    # task_owner:{task_id} -> User A.id
    await redis_client.set(f"task_owner:{task_id}", user_a.user_id)
    
    try:
        # 2. 测试权限控制 (P0)
        
        # 用户 A 申请 Ticket：应该成功
        app.dependency_overrides[get_current_user] = lambda: user_a
        res = await client.post("/api/v1/sse/ticket", params={"task_id": task_id})
        assert res.status_code == 200, f"User A should get ticket: {res.text}"
        ticket_data = res.json()
        assert "ticket" in ticket_data
        ticket = ticket_data["ticket"]
        
        # 用户 B 申请 Ticket：应该返回 403 (无权订阅此任务)
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_b = await client.post("/api/v1/sse/ticket", params={"task_id": task_id})
        assert res_b.status_code == 403, "User B should be forbidden from getting ticket"
        
        # 3. 测试 Ticket 阅后即焚 (P0)
        
        # 用户 A 第一次使用 Ticket：应该成功
        # 注意：GET /events 是流式响应，我们检查初始响应状态
        async with client.stream("GET", f"/api/v1/sse/{task_id}/events", params={"ticket": ticket}) as response:
            assert response.status_code == 200, f"First use of ticket should succeed: {response.status_code}"
            # 显式读取第一行数据，确保握手完成
            async for line in response.aiter_lines():
                if "connect" in line:
                    break
        
        # 立即第二次使用同一个 Ticket：预期返回 403 (Ticket 已被删除)
        async with client.stream("GET", f"/api/v1/sse/{task_id}/events", params={"ticket": ticket}) as response_2:
            assert response_2.status_code == 403, "Second use of same ticket should fail (403)"

        # 4. 测试无效 Ticket
        random_ticket = str(uuid.uuid4())
        async with client.stream("GET", f"/api/v1/sse/{task_id}/events", params={"ticket": random_ticket}) as response_invalid:
            assert response_invalid.status_code == 403, "Invalid ticket should return 403"

    finally:
        # 清理 Redis 中的测试数据
        await redis_client.delete(f"task_owner:{task_id}")
        await redis_client.delete(f"sse_ticket:{ticket}") # 以防万一没被删
