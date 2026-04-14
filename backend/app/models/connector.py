import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SystemConnector(Base):
    __tablename__ = "system_connectors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # e.g. "systeme.io"
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "api" | "database" | "file"
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_env_var: Mapped[str] = mapped_column(String(100), nullable=False)  # env var name holding the key
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Which request types this connector applies to (JSON list)
    applicable_request_types: Mapped[str] = mapped_column(Text, default='["access","deletion","modification","stop_processing"]')

    # Field mapping config (JSON)
    field_mapping: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
