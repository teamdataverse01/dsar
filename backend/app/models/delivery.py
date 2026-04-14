import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DataDelivery(Base):
    __tablename__ = "data_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("dsar_requests.id"), nullable=False, index=True)
    delivery_method: Mapped[str] = mapped_column(String(30), nullable=False)  # "email" | "sharepoint"
    download_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)

    # Encrypted payload (email delivery)
    encrypted_payload: Mapped[bytes | None] = mapped_column(Text, nullable=True)

    # SharePoint delivery
    sharepoint_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)

    # Download tracking
    downloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
