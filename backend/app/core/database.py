from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 异步引擎（供 FastAPI 路由使用）
async_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 同步引擎（专供 Celery Worker 使用，防止事件循环崩溃）
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=10,
    max_overflow=20
)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncSession: # type: ignore
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()