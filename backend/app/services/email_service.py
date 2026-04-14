import logging
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, to_name: str, otp_code: str,
                   reference: str, expiry_minutes: int) -> None:
    subject = f"Your DataVerse DSAR verification code — {reference}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a365d">DataVerse DSAR Portal</h2>
      <p>Hello {to_name},</p>
      <p>We received your data request (<strong>{reference}</strong>).
         To verify your identity, please use the code below.</p>
      <div style="background:#f0f4f8;border-radius:8px;padding:24px;text-align:center;margin:24px 0">
        <p style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#2b6cb0;margin:0">{otp_code}</p>
      </div>
      <p>This code expires in <strong>{expiry_minutes} minutes</strong>.</p>
      <p>If you did not submit this request, you can safely ignore this email.</p>
      <hr style="border:none;border-top:1px solid #e2e8f0">
      <p style="font-size:12px;color:#718096">DataVerse Solutions · DSAR Management System</p>
    </div>
    """

    if not settings.RESEND_API_KEY:
        logger.warning(
            "[DEV — no RESEND_API_KEY] OTP email to %s: code=%s", to_email, otp_code
        )
        return

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
        logger.info("OTP email sent to %s (ref=%s)", to_email, reference)
    except Exception as exc:
        # Log but don't crash — in dev the OTP is shown on-screen anyway
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)


def send_acknowledgement_email(to_email: str, to_name: str, reference: str,
                                request_type: str, due_date: str) -> None:
    subject = f"We received your {request_type} request — {reference}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a365d">DataVerse DSAR Portal</h2>
      <p>Hello {to_name},</p>
      <p>We have received your <strong>{request_type.replace('_',' ').title()}</strong> request
         and your reference number is <strong>{reference}</strong>.</p>
      <p>We will process your request and aim to respond by <strong>{due_date}</strong>
         in line with applicable data protection regulations.</p>
      <p>You can track your request status using your reference number on our portal.</p>
      <hr style="border:none;border-top:1px solid #e2e8f0">
      <p style="font-size:12px;color:#718096">DataVerse Solutions · DSAR Management System</p>
    </div>
    """

    if not settings.RESEND_API_KEY:
        logger.warning("[DEV] Acknowledgement email to %s (ref=%s)", to_email, reference)
        return

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
    except Exception as exc:
        logger.error("Failed to send acknowledgement email: %s", exc)


def send_delivery_email(to_email: str, to_name: str, reference: str,
                         body_html: str) -> None:
    """Send the final response / data delivery email."""
    if not settings.RESEND_API_KEY:
        logger.warning("[DEV] Delivery email to %s (ref=%s)", to_email, reference)
        return

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": [to_email],
            "subject": f"Response to your data request — {reference}",
            "html": body_html,
        })
        logger.info("Delivery email sent to %s (ref=%s)", to_email, reference)
    except Exception as exc:
        logger.error("Failed to send delivery email: %s", exc)
