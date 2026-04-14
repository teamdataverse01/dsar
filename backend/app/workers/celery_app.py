try:
    from celery import Celery
    _celery_available = True
except ImportError:
    _celery_available = False

from app.core.config import settings


def _make_app():
    app = Celery(
        "dsar_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=["app.workers.tasks.workflow_tasks", "app.workers.tasks.delivery_tasks"],
    )
    return app


if _celery_available:
    try:
        celery_app = _make_app()
    except Exception:
        celery_app = None  # type: ignore[assignment]
else:
    celery_app = None  # type: ignore[assignment]

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "expire-stale-deliveries-every-hour": {
            "task": "app.workers.tasks.delivery_tasks.expire_stale_deliveries",
            "schedule": 3600.0,  # every hour
        },
    },
)
