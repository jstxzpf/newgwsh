from fastapi import APIRouter
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.core.celery_app import celery_app
from sqlalchemy import text
from app.core.redis import get_redis
import httpx
import structlog

logger = structlog.get_logger()

router = APIRouter()

@router.get("/status")
async def get_system_status():
    # 1. DB 探活
    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error("system_probe_failed", component="database", error=str(e))
        db_ok = False

    # 2. Redis 探活
    try:
        current_redis = await get_redis()
        await current_redis.ping()
        redis_ok = True
    except Exception as e:
        logger.error("system_probe_failed", component="redis", error=str(e))
        redis_ok = False

    # 3. Celery 探活
    try:
        insp = celery_app.control.inspect()
        stats = insp.stats() or {}
        workers = len(stats)
    except Exception as e:
        logger.error("system_probe_failed", component="celery", error=str(e))
        workers = 0

    # 4. AI 探活 (针对 Ollama)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        ai_ok = resp.status_code == 200
    except Exception as e:
        logger.error("system_probe_failed", component="ollama", error=str(e))
        ai_ok = False

    return {
        "db_connected": db_ok,
        "redis_connected": redis_ok,
        "celery_workers_active": workers,
        "ai_engine_online": ai_ok
    }

