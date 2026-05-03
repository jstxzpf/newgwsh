from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "newgwsh_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.worker"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_concurrency=4,
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=600
)