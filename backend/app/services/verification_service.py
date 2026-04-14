import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_otp
from app.models.dsar_request import DSARRequest, RequestStatus
from app.models.verification import VerificationToken
from app.models.audit_log import AuditLog
from app.services.email_service import send_otp_email

MAX_ATTEMPTS = 5


def send_otp(request: DSARRequest, db: Session) -> dict:
    """Generate OTP, hash it, persist it, send via email."""
    # Invalidate any previous unused tokens
    db.query(VerificationToken).filter_by(
        request_id=request.id, is_used=False
    ).update({"is_used": True})

    otp = generate_otp(settings.OTP_LENGTH)
    otp_hash = _hash_otp(otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    token = VerificationToken(
        request_id=request.id,
        otp_hash=otp_hash,
        expires_at=expires_at,
    )
    db.add(token)

    request.status = RequestStatus.VERIFICATION_PENDING
    db.add(AuditLog(request_id=request.id, action="otp_sent", actor="system",
                    detail=f"OTP sent to {request.subject_email}"))
    db.commit()

    # Send email (falls back to console in dev if RESEND_API_KEY not set)
    send_otp_email(
        to_email=request.subject_email,
        to_name=request.subject_full_name,
        otp_code=otp,
        reference=request.reference,
        expiry_minutes=settings.OTP_EXPIRY_MINUTES,
    )

    result = {"message": "OTP sent to your email address."}
    if settings.is_dev:
        result["dev_otp"] = otp  # Surface in dev so we can test without email
    return result


def verify_otp(request_id: str, otp_code: str, db: Session) -> tuple[bool, str]:
    """
    Returns (success, message).
    On success, marks the request as VERIFIED.
    """
    token = (
        db.query(VerificationToken)
        .filter_by(request_id=request_id, is_used=False)
        .order_by(VerificationToken.created_at.desc())
        .first()
    )

    if not token:
        return False, "No active OTP found. Please request a new one."

    token.attempts += 1

    if token.attempts > MAX_ATTEMPTS:
        token.is_used = True
        db.commit()
        return False, "Too many attempts. Please request a new OTP."

    expires = token.expires_at.replace(tzinfo=timezone.utc) if token.expires_at.tzinfo is None else token.expires_at
    if datetime.now(timezone.utc) > expires:
        token.is_used = True
        db.commit()
        return False, "OTP has expired. Please request a new one."

    if token.otp_hash != _hash_otp(otp_code):
        db.commit()
        return False, f"Invalid OTP. {MAX_ATTEMPTS - token.attempts} attempts remaining."

    # Success
    token.is_used = True
    token.used_at = datetime.now(timezone.utc)

    request = db.query(DSARRequest).filter_by(id=request_id).first()
    request.is_verified = True
    request.verified_at = datetime.now(timezone.utc)
    request.status = RequestStatus.VERIFIED

    db.add(AuditLog(request_id=request_id, action="otp_verified", actor="subject",
                    detail="Identity verified via OTP"))
    db.commit()

    # Automatically run the full workflow after verification (no admin clicks needed)
    # Errors are logged but must not fail the OTP response
    try:
        from app.services.workflow_service import auto_complete
        import logging as _logging
        auto_complete(request, db)
    except Exception as exc:
        _logging.getLogger(__name__).error(
            "auto_complete failed for request %s: %s", request_id, exc, exc_info=True
        )

    return True, "Identity verified successfully."


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()
