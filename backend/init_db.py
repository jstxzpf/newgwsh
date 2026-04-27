import asyncio
import sys
import os

# 确保可以导入 app 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, async_engine
from app.models import *  # 导入所有模型以注册到 Base.metadata

async def init_db():
    print("Creating database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
