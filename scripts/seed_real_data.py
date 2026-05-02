import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.org import Department, SystemUser
from app.models.base import Base

async def seed_data():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # 慎重：这里会清空相关表，仅用于开发环境初始化
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 1. 创建部门
        office = Department(dept_name="办公室", dept_code="OFFICE")
        tech = Department(dept_name="技术科", dept_code="TECH")
        session.add_all([office, tech])
        await session.flush()

        # 2. 创建管理员账号
        admin = SystemUser(
            username="admin",
            full_name="系统管理员",
            password_hash=get_password_hash("admin123"),
            dept_id=office.dept_id,
            role_level=99,
            is_active=True
        )
        user1 = SystemUser(
            username="user1",
            full_name="普通科员",
            password_hash=get_password_hash("user123"),
            dept_id=tech.dept_id,
            role_level=1,
            is_active=True
        )
        session.add_all([admin, user1])
        await session.commit()
        print("Real seed data created successfully: admin/admin123, user1/user123")

if __name__ == "__main__":
    asyncio.run(seed_data())
