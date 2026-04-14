from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.request import DSARIntakeForm, DSARRequestOut
from app.schemas.verification import OTPSendResponse, OTPVerifyRequest, OTPVerifyResponse
from app.core.config import settings
from app.services import intake_service, verification_service, workflow_service

router = APIRouter(prefix="/intake", tags=["Intake"])


@router.post("/requests", response_model=DSARRequestOut, status_code=status.HTTP_201_CREATED)
def submit_request(form: DSARIntakeForm, request: Request, db: Session = Depends(get_db)):
    """Subject submits a new DSAR request — sends acknowledgement + OTP."""
    ip = request.client.host if request.client else None
    dsar = intake_service.create_request(form, db, ip_address=ip)
    # Move to VERIFICATION_PENDING and send acknowledgement email
    dsar = workflow_service.advance(dsar, db, actor="system")
    # Send OTP
    otp_result = verification_service.send_otp(dsar, db)
    # In dev mode, surface the OTP in the response so it shows on-screen
    if settings.is_dev and otp_result.get("dev_otp"):
        dsar.dev_otp = otp_result["dev_otp"]
    return dsar


@router.post("/requests/{request_id}/resend-otp", response_model=OTPSendResponse)
def resend_otp(request_id: str, db: Session = Depends(get_db)):
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    if dsar.is_verified:
        raise HTTPException(status_code=400, detail="Request is already verified")
    result = verification_service.send_otp(dsar, db)
    return OTPSendResponse(**result)


@router.post("/requests/{request_id}/verify-otp", response_model=OTPVerifyResponse)
def verify_otp(request_id: str, body: OTPVerifyRequest, db: Session = Depends(get_db)):
    """
    Subject enters OTP.
    On success, auto_complete() runs the full workflow automatically:
      - looks up / executes the action in systeme.io
      - sends the confirmation email
      - marks the request COMPLETED
    No admin clicks needed for normal-risk requests.
    """
    dsar = intake_service.get_request(request_id, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    # verify_otp internally calls auto_complete after a successful verify
    success, message = verification_service.verify_otp(request_id, body.otp_code, db)
    db.refresh(dsar)
    return OTPVerifyResponse(verified=success, message=message)


@router.get("/requests/{reference}/status", response_model=DSARRequestOut)
def get_status(reference: str, db: Session = Depends(get_db)):
    dsar = intake_service.get_request_by_reference(reference, db)
    if not dsar:
        raise HTTPException(status_code=404, detail="Request not found")
    return dsar
