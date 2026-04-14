from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me"
    PROJECT_NAME: str = "DataVerse DSAR"
    API_V1_PREFIX: str = "/api/v1"

    # Database — SQLite for dev, PostgreSQL for production (Railway sets DATABASE_URL automatically)
    DATABASE_URL: str = "sqlite:///./dsar.db"

    @property
    def db_url(self) -> str:
        url = self.DATABASE_URL
        # Railway provides postgres:// but SQLAlchemy needs postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    # Redis / Celery — optional; background tasks simply won't run if Redis is absent
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email — Resend
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "onboarding@resend.dev"
    EMAIL_FROM_NAME: str = "DataVerse DSAR"

    # systeme.io
    SYSTEMEIO_API_KEY: str = ""
    SYSTEMEIO_BASE_URL: str = "https://api.systeme.io/api"

    # Encryption
    ENCRYPTION_KEY: Optional[str] = None

    # AI (optional)
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_CONFIDENCE_THRESHOLD: float = 0.75

    # OTP
    OTP_EXPIRY_MINUTES: int = 15
    OTP_LENGTH: int = 6

    # SLA (days)
    SLA_DAYS_DEFAULT: int = 30
    SLA_DAYS_URGENT: int = 3

    # SharePoint (stubbed for pilot)
    SHAREPOINT_TENANT_ID: Optional[str] = None
    SHAREPOINT_CLIENT_ID: Optional[str] = None
    SHAREPOINT_CLIENT_SECRET: Optional[str] = None
    SHAREPOINT_SITE_URL: Optional[str] = None

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
