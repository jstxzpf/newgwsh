import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models.base import Base
from app.core.config import settings
import app.models  # 确保所有模型已加载

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    # 注意：确保数据库已启动且可连接
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # 启用 pgvector
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # 创建表
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        # 强制回滚以保持测试隔离
        await session.rollback()
