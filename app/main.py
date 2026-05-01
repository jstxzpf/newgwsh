from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.api.deps import get_async_db
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(title=settings.APP_NAME)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"status": "online", "app_name": settings.APP_NAME}

@app.get("/test-async-db")
async def test_async_db(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(text("SELECT 1"))
    return {"status": "success", "result": result.scalar()}
