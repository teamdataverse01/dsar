"""
Workflow orchestrator — advances a request through its lifecycle stages.

Stages:
  SUBMITTED -> VERIFICATION_PENDING -> VERIFIED -> DATA_LOOKUP
  -> REVIEW_READY -> [ESCALATED] -> APPROVED -> DELIVERED -> COMPLETED

auto_complete() runs all stages automatically after OTP verification
for low/medium risk. High/critical stops at ESCALATED for admin review.
"""
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.dsar_request import DSARRequest, RequestStatus, RiskTier
from app.models.workflow import WorkflowStep
from app.models.audit_log import AuditLog
from app.services import risk_service, connector_service
from app.services.email_service import send_acknowledgement_email, send_delivery_email
from app.services import template_service

logger = logging.getLogger(__name__)


def advance(request: DSARRequest, db: Session, actor: str = "system",
            notes: str | None = None) -> DSARRequest:
    """Move the request to the next logical stage (single step)."""
    current = request.status

    if current == RequestStatus.SUBMITTED:
        _transition(request, db, RequestStatus.VERIFICATION_PENDING, actor, notes)
        due = request.due_date.strftime("%d %B %Y") if request.due_date else "within 30 days"
        send_acknowledgement_email(
            request.subject_email, request.subject_full_name,
            request.reference, request.request_type.value, due
        )

    elif current == RequestStatus.VERIFIED:
        _transition(request, db, RequestStatus.DATA_LOOKUP, actor, notes)
        _run_data_lookup(request, db)

    elif current == RequestStatus.DATA_LOOKUP:
        tier, escalation_reason = risk_service.assess_risk(request)
        request.risk_tier = tier
        if tier in (RiskTier.HIGH, RiskTier.CRITICAL):
            request.is_escalated = True
            request.escalation_reason = escalation_reason
            _transition(request, db, RequestStatus.ESCALATED, actor,
                        f"Auto-escalated: {escalation_reason}")
        else:
            _transition(request, db, RequestStatus.REVIEW_READY, actor, notes)

    elif current in (RequestStatus.REVIEW_READY, RequestStatus.ESCALATED):
        _transition(request, db, RequestStatus.APPROVED, actor, notes)

    elif current == RequestStatus.APPROVED:
        _transition(request, db, RequestStatus.DELIVERED, actor, notes)
        _send_completion_email(request, db)

    elif current == RequestStatus.DELIVERED:
        request.completed_at = datetime.now(timezone.utc)
        _transition(request, db, RequestStatus.COMPLETED, actor, notes)

    db.commit()
    db.refresh(request)
    return request


def auto_complete(request: DSARRequest, db: Session) -> DSARRequest:
    """
    Called automatically after OTP verification.
    Runs all stages without admin input for low/medium risk.
    High/critical risk stops at ESCALATED and waits for admin.
    """
    logger.info("Auto-completing request %s from status %s", request.reference, request.status.value)

    # VERIFIED -> DATA_LOOKUP (runs the actual systeme.io action)
    if request.status == RequestStatus.VERIFIED:
        _transition(request, db, RequestStatus.DATA_LOOKUP, "system", "Auto: post-verification lookup")
        try:
            _run_data_lookup(request, db)
        except Exception as exc:
            logger.error("Data lookup failed for %s: %s", request.reference, exc, exc_info=True)
            db.add(AuditLog(
                request_id=request.id,
                action="data_lookup_failed",
                actor="system",
                detail=str(exc),
            ))
        db.commit()
        db.refresh(request)

    # DATA_LOOKUP -> risk assess -> REVIEW_READY or ESCALATED
    if request.status == RequestStatus.DATA_LOOKUP:
        tier, escalation_reason = risk_service.assess_risk(request)
        request.risk_tier = tier
        if tier in (RiskTier.HIGH, RiskTier.CRITICAL):
            request.is_escalated = True
            request.escalation_reason = escalation_reason
            _transition(request, db, RequestStatus.ESCALATED, "system",
                        f"Auto-escalated: {escalation_reason}")
            db.commit()
            db.refresh(request)
            logger.info("Request %s escalated (%s) — admin review required", request.reference, escalation_reason)
            return request  # Stop here — admin must review escalated requests
        else:
            _transition(request, db, RequestStatus.REVIEW_READY, "system", "Auto: risk assessed")
            db.commit()
            db.refresh(request)

    # REVIEW_READY -> APPROVED -> DELIVERED -> COMPLETED (all automatic for normal risk)
    if request.status == RequestStatus.REVIEW_READY:
        _transition(request, db, RequestStatus.APPROVED, "system", "Auto: approved")
        db.commit()
        db.refresh(request)

    if request.status == RequestStatus.APPROVED:
        _transition(request, db, RequestStatus.DELIVERED, "system", "Auto: delivered")
        _send_completion_email(request, db)
        db.commit()
        db.refresh(request)

    if request.status == RequestStatus.DELIVERED:
        request.completed_at = datetime.now(timezone.utc)
        _transition(request, db, RequestStatus.COMPLETED, "system", "Auto: completed")
        db.commit()
        db.refresh(request)

    logger.info("Request %s auto-completed with status %s", request.reference, request.status.value)
    return request


def reject(request: DSARRequest, db: Session, actor: str,
           reason: str, partial: bool = False) -> DSARRequest:
    new_status = RequestStatus.PARTIAL_REJECTION if partial else RequestStatus.REJECTED
    _transition(request, db, new_status, actor, reason)
    db.commit()
    db.refresh(request)
    return request


def _run_data_lookup(request: DSARRequest, db: Session) -> None:
    result = connector_service.run_lookup(
        request_type=request.request_type.value,
        subject_email=request.subject_email,
    )
    step = WorkflowStep(
        request_id=request.id,
        stage="data_lookup",
        status="completed",
        notes=json.dumps(result),
        performed_by="system",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(step)
    db.add(AuditLog(
        request_id=request.id,
        action="data_lookup_completed",
        actor="system",
        detail=f"systeme.io: found={result.get('found', False)}, deleted={result.get('deleted', 'n/a')}"
    ))


def _send_completion_email(request: DSARRequest, db: Session) -> None:
    """Send the final response email to the subject."""
    try:
        response_text = template_service.get_response_template(request)
        # Convert plain text template to simple HTML
        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#1a365d">DataVerse DSAR Portal</h2>
          <pre style="font-family:Arial,sans-serif;white-space:pre-wrap;font-size:14px">{response_text}</pre>
          <hr style="border:none;border-top:1px solid #e2e8f0">
          <p style="font-size:12px;color:#718096">
            Reference: {request.reference} | DataVerse Solutions
          </p>
        </div>
        """
        send_delivery_email(
            to_email=request.subject_email,
            to_name=request.subject_full_name,
            reference=request.reference,
            body_html=html_body,
        )
        db.add(AuditLog(
            request_id=request.id,
            action="response_delivered",
            actor="system",
            detail=f"Confirmation email sent to {request.subject_email}"
        ))
    except Exception as exc:
        logger.error("Failed to send completion email for %s: %s", request.reference, exc)


def _transition(request: DSARRequest, db: Session,
                new_status: RequestStatus, actor: str, notes: str | None) -> None:
    old_status = request.status.value
    request.status = new_status
    request.updated_at = datetime.now(timezone.utc)

    step = WorkflowStep(
        request_id=request.id,
        stage=new_status.value,
        status="completed",
        notes=notes,
        performed_by=actor,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(step)
    db.add(AuditLog(
        request_id=request.id,
        action="status_changed",
        actor=actor,
        detail=f"{old_status} -> {new_status.value}",
    ))
    logger.info("Request %s: %s -> %s (by %s)", request.reference, old_status, new_status.value, actor)
