import logging
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services import workflow_service
from app.models.dsar_request import DSARRequest, RequestStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.workflow_tasks.run_data_lookup")
def run_data_lookup(request_id: str) -> dict:
    """Async task: run the systeme.io lookup for a verified request."""
    db = SessionLocal()
    try:
        request = db.query(DSARRequest).filter_by(id=request_id).first()
        if not request:
            return {"error": "Request not found"}
        if request.status != RequestStatus.VERIFIED:
            return {"skipped": True, "reason": f"Status is {request.status.value}, expected verified"}

        workflow_service.advance(request, db, actor="celery_worker")
        return {"success": True, "new_status": request.status.value}
    except Exception as exc:
        logger.error("run_data_lookup failed for %s: %s", request_id, exc)
        return {"error": str(exc)}
    finally:
        db.close()
