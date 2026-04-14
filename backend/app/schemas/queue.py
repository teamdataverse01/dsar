from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.dsar_request import RequestType, RequestStatus, RiskTier


class QueueItem(BaseModel):
    id: str
    reference: str
    subject_email: str
    request_type: RequestType
    status: RequestStatus
    risk_tier: Optional[RiskTier] = None
    is_escalated: bool
    is_verified: bool
    submitted_at: datetime
    due_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    sla_breached: bool = False

    model_config = {"from_attributes": True}


class QueueResponse(BaseModel):
    total: int
    items: List[QueueItem]
