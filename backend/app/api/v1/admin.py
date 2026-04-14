from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin_user import AdminUser
from app.models.dsar_request import DSARRequest
from app.models.audit_log import AuditLog
from app.models.workflow import WorkflowStep
from app.models.response_draft import ResponseDraft
from app.schemas.request import DSARRequestDetail, AdminNoteUpdate
from app.schemas.queue import QueueResponse
from app.services import (
    intake_service, workflow_service, queue_service,
    delivery_service, qa_service, template_service, ai_service
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Queue ─────────────────────────────────────────────────────────────────────

@router.get("/queue", response_model=QueueResponse)
def get_queue(
    status_filter: str | None = Query(None),
    risk_filter: str | None = Query(None),
    escalated_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    return queue_service.get_queue(db, status_filter, risk_filter, escalated_only, page, page_size)


# ── Request detail ─────────────────────────────────────────────────────────────

@router.get("/requests/{request_id}", response_model=DSARRequestDetail)
def get_request(request_id: str, db: Session = Depends(get_db),
                _admin: AdminUser = Depends(get_current_admin)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    return dsar


@router.get("/requests/{request_id}/audit-log")
def get_audit_log(request_id: str, db: Session = Depends(get_db),
                  _admin: AdminUser = Depends(get_current_admin)):
    logs = db.query(AuditLog).filter_by(request_id=request_id).order_by(AuditLog.timestamp).all()
    return [{"action": l.action, "actor": l.actor, "detail": l.detail,
             "timestamp": l.timestamp} for l in logs]


@router.get("/requests/{request_id}/workflow")
def get_workflow(request_id: str, db: Session = Depends(get_db),
                 _admin: AdminUser = Depends(get_current_admin)):
    steps = db.query(WorkflowStep).filter_by(request_id=request_id).order_by(WorkflowStep.started_at).all()
    return [{"stage": s.stage, "status": s.status, "notes": s.notes,
             "performed_by": s.performed_by, "completed_at": s.completed_at} for s in steps]


@router.patch("/requests/{request_id}/notes")
def update_notes(request_id: str, body: AdminNoteUpdate, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(get_current_admin)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    dsar.admin_notes = body.admin_notes
    db.commit()
    return {"message": "Notes updated"}


# ── Workflow actions ───────────────────────────────────────────────────────────

@router.post("/requests/{request_id}/advance")
def advance_workflow(request_id: str, notes: str | None = None,
                     db: Session = Depends(get_db),
                     admin: AdminUser = Depends(get_current_admin)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    dsar = workflow_service.advance(dsar, db, actor=admin.email, notes=notes)
    return {"status": dsar.status.value, "message": "Workflow advanced"}


@router.post("/requests/{request_id}/reject")
def reject_request(request_id: str, reason: str, partial: bool = False,
                   db: Session = Depends(get_db),
                   admin: AdminUser = Depends(get_current_admin)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    dsar = workflow_service.reject(dsar, db, actor=admin.email, reason=reason, partial=partial)
    return {"status": dsar.status.value, "message": "Request rejected"}


# ── QA checks ─────────────────────────────────────────────────────────────────

@router.get("/requests/{request_id}/qa-check")
def run_qa(request_id: str, db: Session = Depends(get_db),
           _admin: AdminUser = Depends(get_current_admin)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    result = qa_service.run_checks(dsar)
    return result.to_dict()


# ── AI draft ──────────────────────────────────────────────────────────────────

@router.post("/requests/{request_id}/generate-draft")
def generate_draft(request_id: str, db: Session = Depends(get_db),
                   admin: AdminUser = Depends(get_current_admin)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")

    template_text = template_service.get_response_template(dsar)
    draft_result = ai_service.generate_draft(
        request_type=dsar.request_type.value,
        subject_name=dsar.subject_full_name,
        reference=dsar.reference,
        template_draft=template_text,
    )

    draft = ResponseDraft(
        request_id=request_id,
        template_type=dsar.request_type.value,
        draft_text=draft_result["draft_text"],
        is_ai_generated=not draft_result.get("skipped", True),
        confidence_score=draft_result.get("confidence_score"),
        ai_risk_level=draft_result.get("ai_risk_level"),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {
        "draft_id": draft.id,
        "draft_text": draft.draft_text,
        "is_ai_generated": draft.is_ai_generated,
        "confidence_score": draft.confidence_score,
        "ai_risk_level": draft.ai_risk_level,
        "needs_review": (draft.confidence_score or 0) < 0.75 or draft.ai_risk_level == "high",
    }


@router.post("/requests/{request_id}/approve-draft/{draft_id}")
def approve_draft(request_id: str, draft_id: str, edited_text: str | None = None,
                  db: Session = Depends(get_db),
                  admin: AdminUser = Depends(get_current_admin)):
    from datetime import datetime, timezone
    draft = db.query(ResponseDraft).filter_by(id=draft_id, request_id=request_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.review_status = "approved"
    draft.reviewed_by = admin.email
    draft.reviewed_at = datetime.now(timezone.utc)
    draft.final_text = edited_text or draft.draft_text
    db.commit()
    return {"message": "Draft approved"}


# ── Delivery ──────────────────────────────────────────────────────────────────

@router.post("/requests/{request_id}/deliver")
def deliver(request_id: str, method: str = "email", db: Session = Depends(get_db),
            admin: AdminUser = Depends(get_current_admin)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")

    qa = qa_service.run_checks(dsar)
    if not qa.passed:
        raise HTTPException(status_code=400, detail={"qa_failures": qa.failures})

    # Get approved draft text (or fallback to template)
    approved = (db.query(ResponseDraft)
                .filter_by(request_id=request_id, review_status="approved")
                .order_by(ResponseDraft.created_at.desc()).first())
    response_text = approved.final_text if approved else template_service.get_response_template(dsar)

    if method == "sharepoint":
        delivery = delivery_service.deliver_via_sharepoint(dsar, {}, db)
    else:
        delivery = delivery_service.deliver_via_email(dsar, {}, response_text, db)

    workflow_service.advance(dsar, db, actor=admin.email, notes=f"Delivered via {method}")
    return {"delivery_id": delivery.id, "method": delivery.delivery_method,
            "message": f"Delivered via {method}"}
