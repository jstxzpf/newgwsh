from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/status")
async def get_system_status():
    return {
        "db_connected": True, 
        "redis_connected": True, 
        "celery_workers_active": 1, 
        "ai_engine_online": True
    }
