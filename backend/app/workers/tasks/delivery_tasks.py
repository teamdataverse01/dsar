import logging
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.delivery_service import expire_stale_deliveries as _expire

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.delivery_tasks.expire_stale_deliveries")
def expire_stale_deliveries() -> dict:
    """Hourly: expire SharePoint links that have passed their 72h window."""
    db = SessionLocal()
    try:
        count = _expire(db)
        logger.info("Expired %d stale deliveries", count)
        return {"expired_count": count}
    except Exception as exc:
        logger.error("expire_stale_deliveries failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()
