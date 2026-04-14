from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.dsar_request import RequestType, RequestStatus, RiskTier, DataSensitivity, SubjectPersona


class DSARIntakeForm(BaseModel):
    """What the subject submits on the intake form."""
    subject_full_name: str
    subject_email: EmailStr
    subject_phone: Optional[str] = None
    request_type: RequestType
    data_sensitivity: DataSensitivity = DataSensitivity.INTERNAL
    subject_persona: SubjectPersona = SubjectPersona.GENERAL_PUBLIC
    data_categories: Optional[List[str]] = None  # e.g. ["contact_info", "purchase_history"]
    special_context: Optional[str] = None  # selected from dropdown

    @field_validator("subject_full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name is required")
        return v.strip()


class DSARRequestOut(BaseModel):
    """What we return after submission / in status checks."""
    id: str
    reference: str
    request_type: RequestType
    status: RequestStatus
    risk_tier: Optional[RiskTier] = None
    is_escalated: bool
    is_verified: bool
    submitted_at: datetime
    due_date: Optional[datetime] = None
    # Dev-only: OTP returned in-browser so no email is needed for local testing
    dev_otp: Optional[str] = None

    model_config = {"from_attributes": True}


class DSARRequestDetail(DSARRequestOut):
    """Full detail — admin only."""
    subject_full_name: str
    subject_email: str
    subject_phone: Optional[str] = None
    data_categories: Optional[str] = None
    systems_in_scope: Optional[str] = None
    special_context: Optional[str] = None
    escalation_reason: Optional[str] = None
    admin_notes: Optional[str] = None
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminNoteUpdate(BaseModel):
    admin_notes: str
