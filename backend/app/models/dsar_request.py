import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class RequestType(str, enum.Enum):
    ACCESS = "access"
    DELETION = "deletion"
    MODIFICATION = "modification"
    STOP_PROCESSING = "stop_processing"


class RequestStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    DATA_LOOKUP = "data_lookup"
    REVIEW_READY = "review_ready"
    ESCALATED = "escalated"
    APPROVED = "approved"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    REJECTED = "rejected"
    PARTIAL_REJECTION = "partial_rejection"
    CLOSED = "closed"


class RiskTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataSensitivity(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"


class SubjectPersona(str, enum.Enum):
    GENERAL_PUBLIC = "general_public"
    VULNERABLE_ADULT = "vulnerable_adult"
    MINOR = "minor"
    EMPLOYEE = "employee"
    SUBJECT_OF_INVESTIGATION = "subject_of_investigation"


class DSARRequest(Base):
    __tablename__ = "dsar_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Subject information
    subject_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Request classification
    request_type: Mapped[RequestType] = mapped_column(SAEnum(RequestType), nullable=False)
    data_sensitivity: Mapped[DataSensitivity] = mapped_column(
        SAEnum(DataSensitivity), default=DataSensitivity.INTERNAL
    )
    subject_persona: Mapped[SubjectPersona] = mapped_column(
        SAEnum(SubjectPersona), default=SubjectPersona.GENERAL_PUBLIC
    )

    # Additional context (structured, not free text)
    data_categories: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    systems_in_scope: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    special_context: Mapped[str | None] = mapped_column(String(500), nullable=True)  # dropdown selection

    # Workflow state
    status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus), default=RequestStatus.SUBMITTED)
    risk_tier: Mapped[RiskTier | None] = mapped_column(SAEnum(RiskTier), nullable=True)
    is_escalated: Mapped[bool] = mapped_column(default=False)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(36), nullable=True)  # AdminUser.id

    # Verification state
    is_verified: Mapped[bool] = mapped_column(default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # SLA
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Internal notes
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
