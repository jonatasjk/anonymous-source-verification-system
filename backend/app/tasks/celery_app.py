from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "asvs",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.pipeline",
        "app.tasks.ots_confirmation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Celery Beat schedule for OTS confirmation polling
    beat_schedule={
        "poll-ots-confirmations": {
            "task": "app.tasks.ots_confirmation.poll_ots_confirmations",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)
