from pydantic import BaseModel


class OTPVerifyRequest(BaseModel):
    otp_code: str


class OTPVerifyResponse(BaseModel):
    verified: bool
    message: str


class OTPSendResponse(BaseModel):
    message: str
    dev_otp: str | None = None  # Only populated in development mode
