"""
Delivery service — packages and sends data to the subject.

Delivery methods:
  1. Encrypted email — data JSON encrypted with Fernet, key sent separately
  2. SharePoint link  — stubbed for pilot, wired for production
"""
import json
import secrets
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.security import encrypt_data
from app.core.config import settings
from app.models.dsar_request import DSARRequest
from app.models.delivery import DataDelivery
from app.models.audit_log import AuditLog
from app.services.email_service import send_delivery_email

logger = logging.getLogger(__name__)

SHAREPOINT_EXPIRY_HOURS = 72


def deliver_via_email(request: DSARRequest, data_payload: dict,
                      response_text: str, db: Session) -> DataDelivery:
    """Encrypt data payload and email it to the subject."""
    raw = json.dumps(data_payload, indent=2, default=str).encode("utf-8")
    encrypted = encrypt_data(raw)
    download_token = secrets.token_urlsafe(32)

    delivery = DataDelivery(
        request_id=request.id,
        delivery_method="email",
        download_token=download_token,
        encrypted_payload=encrypted.decode("utf-8"),
    )
    db.add(delivery)

    # Build email body
    body_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a365d">DataVerse DSAR Portal — Response</h2>
      <p>{response_text.replace(chr(10), '<br>')}</p>
      <hr style="border:none;border-top:1px solid #e2e8f0">
      <p style="font-size:12px;color:#718096">
        Reference: {request.reference} · DataVerse Solutions
      </p>
    </div>
    """

    send_delivery_email(request.subject_email, request.subject_full_name,
                        request.reference, body_html)

    db.add(AuditLog(
        request_id=request.id,
        action="data_delivered_email",
        actor="system",
        detail=f"Delivery email sent to {request.subject_email}"
    ))
    db.commit()
    return delivery


def deliver_via_sharepoint(request: DSARRequest, data_payload: dict,
                            db: Session) -> DataDelivery:
    """
    Stub: upload to SharePoint and return a time-limited download link.
    Wire SHAREPOINT_* env vars to activate in production.
    """
    download_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SHAREPOINT_EXPIRY_HOURS)

    # TODO: replace stub with real SharePoint Graph API upload
    stub_url = f"https://sharepoint.example.com/dsar/{download_token}"
    logger.warning("SharePoint delivery is STUBBED — token=%s", download_token)

    delivery = DataDelivery(
        request_id=request.id,
        delivery_method="sharepoint",
        download_token=download_token,
        sharepoint_url=stub_url,
        expires_at=expires_at,
    )
    db.add(delivery)
    db.add(AuditLog(
        request_id=request.id,
        action="data_delivery_sharepoint_created",
        actor="system",
        detail=f"SharePoint link created, expires {expires_at.isoformat()}"
    ))
    db.commit()
    return delivery


def record_download(token: str, db: Session) -> DataDelivery | None:
    delivery = db.query(DataDelivery).filter_by(download_token=token).first()
    if not delivery:
        return None
    if delivery.is_expired:
        return delivery  # caller checks .is_expired

    delivery.downloaded = True
    delivery.download_count += 1
    delivery.downloaded_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        request_id=delivery.request_id,
        action="data_downloaded",
        actor="subject",
        detail=f"Download #{delivery.download_count}"
    ))
    db.commit()
    return delivery


def expire_stale_deliveries(db: Session) -> int:
    """Called by Celery beat — mark expired SharePoint deliveries."""
    now = datetime.now(timezone.utc)
    all_deliveries = (
        db.query(DataDelivery)
        .filter(DataDelivery.delivery_method == "sharepoint", DataDelivery.is_expired.is_(False))
        .all()
    )
    # Compare timezone-naive SQLite datetimes safely
    expired = [
        d for d in all_deliveries
        if d.expires_at is not None and
           (d.expires_at.replace(tzinfo=timezone.utc) if d.expires_at.tzinfo is None else d.expires_at) <= now
    ]
    for d in expired:
        d.is_expired = True
        db.add(AuditLog(
            request_id=d.request_id,
            action="delivery_expired",
            actor="system",
            detail="SharePoint link expired automatically"
        ))
    db.commit()
    return len(expired)
