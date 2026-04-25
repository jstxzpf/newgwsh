from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. 异步引擎与会话 (供 FastAPI 路由层使用)
async_engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 2. 同步引擎与会话 (供 Celery Worker 使用，防止事件循环阻塞)
sync_engine = create_engine(settings.SYNC_DATABASE_URI, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# FastAPI 依赖注入
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

# Celery 依赖使用
def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
