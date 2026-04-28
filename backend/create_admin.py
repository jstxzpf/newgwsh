import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User, Department
from app.core.security import pwd_context
from app.core.config import settings

async def create_first_admin():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 1. 检查或创建部门
        result = await db.execute(select(Department).where(Department.dept_name == "办公室"))
        dept = result.scalars().first()
        if not dept:
            dept = Department(dept_name="办公室", dept_code="OFFICE")
            db.add(dept)
            await db.commit()
            await db.refresh(dept)
            print("Department '办公室' created.")

        # 2. 检查或创建管理员
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalars().first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=pwd_context.hash("admin123"),
                dept_id=dept.dept_id,
                role_level=99 # 管理员级别提升至 99
            )
            db.add(admin)
            await db.commit()
            print("Admin user 'admin' created with password 'admin123'.")
        else:
            print("Admin user 'admin' already exists.")

if __name__ == "__main__":
    asyncio.run(create_first_admin())
