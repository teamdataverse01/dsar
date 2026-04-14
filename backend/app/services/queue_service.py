from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.dsar_request import DSARRequest, RequestStatus
from app.schemas.queue import QueueItem, QueueResponse


def get_queue(
    db: Session,
    status_filter: str | None = None,
    risk_filter: str | None = None,
    escalated_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> QueueResponse:
    query = db.query(DSARRequest).filter(
        DSARRequest.status.notin_([RequestStatus.COMPLETED, RequestStatus.CLOSED])
    )

    if status_filter:
        query = query.filter(DSARRequest.status == status_filter)
    if risk_filter:
        query = query.filter(DSARRequest.risk_tier == risk_filter)
    if escalated_only:
        query = query.filter(DSARRequest.is_escalated.is_(True))

    # Sort: escalated first, then by due_date ascending (soonest deadline first)
    query = query.order_by(
        desc(DSARRequest.is_escalated),
        DSARRequest.due_date.asc().nulls_last(),
    )

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    now = datetime.now(timezone.utc)
    queue_items = []
    for r in items:
        days_remaining = None
        sla_breached = False
        if r.due_date:
            due = r.due_date.replace(tzinfo=timezone.utc) if r.due_date.tzinfo is None else r.due_date
            delta = (due - now).days
            days_remaining = delta
            sla_breached = delta < 0

        queue_items.append(QueueItem(
            id=r.id,
            reference=r.reference,
            subject_email=r.subject_email,
            request_type=r.request_type,
            status=r.status,
            risk_tier=r.risk_tier,
            is_escalated=r.is_escalated,
            is_verified=r.is_verified,
            submitted_at=r.submitted_at,
            due_date=r.due_date,
            days_remaining=days_remaining,
            sla_breached=sla_breached,
        ))

    return QueueResponse(total=total, items=queue_items)
