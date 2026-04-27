import os
import sys
import asyncio
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

# 1. 环境与路径初始化
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ["POSTGRES_DB"] = "taixing_nbs_test"
os.environ["APP_ENV"] = "testing"

# 【针对 Windows 的终极优化】使用 SelectorEventLoop 避免 Proactor 退出时的 Socket 挂起
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import settings
from app.core.database import Base

# --- 基础基础设施 (Session 级) ---

@pytest.fixture(scope="session", autouse=True)
def setup_infrastructure():
    """确保容器启动并创建测试库"""
    try:
        from tests.scripts.env_prep import ensure_containers_running
    except ImportError:
        from backend.tests.scripts.env_prep import ensure_containers_running
    ensure_containers_running()
    
    sync_url = f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        if not conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{settings.POSTGRES_DB}'")).fetchone():
            conn.execute(text(f"CREATE DATABASE {settings.POSTGRES_DB}"))
    engine.dispose()
    yield

# --- 测试隔离 (Function 级 - 首端清理策略) ---

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    # 每次测试开始前，先用同步引擎强力重置数据库（避免在 Teardown 时卡住）
    sync_test_url = f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    sync_engine = create_engine(sync_test_url, isolation_level="AUTOCOMMIT")
    with sync_engine.connect() as conn:
        # 强制踢掉所有残留连接，防止由于连接占用导致 TRUNCATE/DROP 阻塞
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{settings.POSTGRES_DB}'
              AND pid <> pg_backend_pid();
        """))
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public;"))
    sync_engine.dispose()

    # 创建当前测试用的异步引擎
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 【核心改变】Teardown 阶段不做任何重型数据库操作，只做基础释放
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session_factory(db_engine):
    return async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(autouse=True)
async def stable_mocks(db_session_factory, db_engine):
    import app.core.database
    import app.core.redis
    import app.api.dependencies
    from fastapi import BackgroundTasks
    from app.services.audit_service import AuditService
    import redis.asyncio as aioredis
    
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    
    patches = [
        patch("app.core.database.AsyncSessionLocal", return_value=db_session_factory()),
        patch("app.core.database.async_engine", db_engine),
        patch("app.core.redis.redis_client", redis_client),
        patch("app.api.dependencies.redis_client", redis_client),
        patch.object(BackgroundTasks, "add_task", lambda self, f, *a, **k: None),
        patch.object(AuditService, "write_audit_log", MagicMock())
    ]
    
    for p in patches: p.start()
    
    from app.main import app
    from app.api.dependencies import get_async_db
    from app.core.redis import get_redis
    app.dependency_overrides[get_async_db] = lambda: db_session_factory()
    app.dependency_overrides[get_redis] = lambda: redis_client
    
    yield
    
    app.dependency_overrides.clear()
    for p in patches: p.stop()
    await redis_client.aclose()

@pytest_asyncio.fixture(scope="function")
async def client():
    from app.main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
