import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ResponseDraft(Base):
    __tablename__ = "response_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("dsar_requests.id"), nullable=False, index=True)

    # Content
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "access_response"
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # AI scoring
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low / medium / high

    # Review state
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / approved / rejected / edited
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # admin-edited version

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
