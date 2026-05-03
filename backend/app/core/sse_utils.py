import uuid
import json
from app.core.locks import redis_client

async def generate_sse_ticket(task_id: str, user_id: int) -> str:
    ticket = str(uuid.uuid4())
    key = f"ticket:{ticket}"
    value = json.dumps({"task_id": task_id, "user_id": user_id})
    await redis_client.set(key, value, ex=15) # 15 秒存活
    return ticket

async def consume_sse_ticket(ticket: str) -> dict | None:
    key = f"ticket:{ticket}"
    value = await redis_client.get(key)
    if value:
        await redis_client.delete(key) # 阅后即焚
        return json.loads(value)
    return None

async def verify_task_owner(task_id: str, user_id: int) -> bool:
    owner_str = await redis_client.get(f"task_owner:{task_id}")
    return owner_str is not None and int(owner_str) == user_id