import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import AsyncSessionLocal
from app.models import SystemUser, Department

async def seed():
    async with AsyncSessionLocal() as session:
        # 种子数据逻辑，后续执行
        print("Seeding ready.")

if __name__ == "__main__":
    asyncio.run(seed())