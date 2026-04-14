import json
import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dsar_request import DSARRequest, RequestStatus
from app.models.audit_log import AuditLog
from app.schemas.request import DSARIntakeForm


def _generate_reference() -> str:
    """Generate a human-readable reference like DVS-2024-A3X9."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    year = datetime.now(timezone.utc).year
    return f"DVS-{year}-{suffix}"


def create_request(form: DSARIntakeForm, db: Session, ip_address: str | None = None) -> DSARRequest:
    """Validate intake form and create a new DSAR request."""
    # Ensure unique reference
    for _ in range(5):
        ref = _generate_reference()
        if not db.query(DSARRequest).filter_by(reference=ref).first():
            break

    due_date = datetime.now(timezone.utc) + timedelta(days=settings.SLA_DAYS_DEFAULT)

    request = DSARRequest(
        reference=ref,
        subject_full_name=form.subject_full_name,
        subject_email=form.subject_email.lower(),
        subject_phone=form.subject_phone,
        request_type=form.request_type,
        data_sensitivity=form.data_sensitivity,
        subject_persona=form.subject_persona,
        data_categories=json.dumps(form.data_categories) if form.data_categories else None,
        special_context=form.special_context,
        status=RequestStatus.SUBMITTED,
        due_date=due_date,
    )
    db.add(request)
    db.flush()

    _log(db, request.id, "request_submitted", "subject", ip_address=ip_address,
         detail=f"Request type: {form.request_type.value}")

    db.commit()
    db.refresh(request)
    return request


def get_request(request_id: str, db: Session) -> DSARRequest | None:
    return db.query(DSARRequest).filter_by(id=request_id).first()


def get_request_by_reference(reference: str, db: Session) -> DSARRequest | None:
    return db.query(DSARRequest).filter_by(reference=reference).first()


def _log(db: Session, request_id: str, action: str, actor: str,
         detail: str | None = None, ip_address: str | None = None) -> None:
    db.add(AuditLog(request_id=request_id, action=action, actor=actor,
                    detail=detail, ip_address=ip_address))
