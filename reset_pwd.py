import asyncio
from app.core.database import AsyncSessionLocal
from app.models.org import SystemUser
from app.core.security import get_password_hash
from sqlalchemy import select

async def reset_password():
    async with AsyncSessionLocal() as db:
        stmt = select(SystemUser).where(SystemUser.username == "admin")
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            user.password_hash = get_password_hash("Admin123!")
            print("Password reset for admin to Admin123!")
            await db.commit()
        else:
            print("User admin not found")

if __name__ == "__main__":
    asyncio.run(reset_password())
