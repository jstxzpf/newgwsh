import asyncio
from app.core.database import AsyncSessionLocal
from app.models.org import SystemUser
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(SystemUser))
        users = res.scalars().all()
        for u in users:
            print(f"User: {u.username}, Active: {u.is_active}, Role: {u.role_level}")

if __name__ == "__main__":
    asyncio.run(check())
