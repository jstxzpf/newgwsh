import asyncio
from sqlalchemy import text
from app.core.database import async_engine, sync_engine

async def test_async_conn():
    print("Testing Async Connection...")
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Async Result: {result.scalar()}")
    except Exception as e:
        print(f"Async Connection Failed: {e}")

def test_sync_conn():
    print("Testing Sync Connection...")
    try:
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Sync Result: {result.scalar()}")
    except Exception as e:
        print(f"Sync Connection Failed: {e}")

if __name__ == "__main__":
    # 在 Docker 外部运行时，可能需要修改 localhost 为正确的 IP 或跳过验证
    print("Verification script ready. Note: Run this inside the container if localhost is not mapped.")
    # asyncio.run(test_async_conn())
    # test_sync_conn()
