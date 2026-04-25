from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/config")
async def get_lock_config():
    return {
        "lock_ttl_seconds": settings.LOCK_TTL_SECONDS,
        "heartbeat_interval_seconds": settings.HEARTBEAT_INTERVAL_SECONDS,
        "retry_backoff_base_seconds": settings.RETRY_BACKOFF_BASE_SECONDS,
        "retry_backoff_max_seconds": settings.RETRY_BACKOFF_MAX_SECONDS
    }
