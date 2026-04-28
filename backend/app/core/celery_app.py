from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.worker"]
)

celery_app.conf.task_routes = {
    "app.tasks.worker.*": {"queue": "taixing_tasks"}
}
celery_app.conf.update(
    task_track_started=True,
    task_soft_time_limit=600,
    task_time_limit=900,
    beat_schedule={
        "cleanup-expired-files": {
            "task": "app.tasks.worker.cleanup_expired_files_task",
            "schedule": crontab(
                hour=settings.CELERY_CLEANUP_CRONTAB_HOUR, 
                minute=settings.CELERY_CLEANUP_CRONTAB_MINUTE
            ),
        },
    }
)
