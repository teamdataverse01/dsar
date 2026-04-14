"""
Dev-mode auto-bootstrap:
- Generates ENCRYPTION_KEY in memory if not configured
- Creates a default admin account on first boot
- Seeds 3 test contacts in systeme.io so there is real data to test against
"""
import logging
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# These are the test contacts seeded into systeme.io on first boot.
# Use salaudeenmubarakstar@gmail.com as your test email on the intake form
# — it is the only address verified in Resend test mode, so you will
# receive the real OTP email and the final confirmation email.
SEED_CONTACTS = [
    {"email": "salaudeenmubarakstar@gmail.com", "firstName": "Mubarak",  "lastName": "Salaudeen"},
    {"email": "alice.demo@mailinator.com",      "firstName": "Alice",    "lastName": "Demo"},
    {"email": "bob.demo@mailinator.com",         "firstName": "Bob",      "lastName": "Demo"},
]


def ensure_encryption_key() -> None:
    if not settings.ENCRYPTION_KEY:
        key = Fernet.generate_key().decode()
        settings.ENCRYPTION_KEY = key  # type: ignore[assignment]
        logger.warning(
            "[DEV] No ENCRYPTION_KEY — generated ephemeral key: %s\n"
            "Add ENCRYPTION_KEY=%s to backend/.env to persist it.", key, key
        )


def seed_default_admin(db: Session) -> None:
    from app.models.admin_user import AdminUser
    from app.core.security import hash_password
    if db.query(AdminUser).count() > 0:
        return
    admin = AdminUser(
        email="admin@test.com",
        full_name="Dev Admin",
        hashed_password=hash_password("password123"),
        is_superadmin=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.warning("[DEV] Admin created: admin@test.com / password123")


def seed_systemeio_contacts() -> None:
    """Create 3 test contacts in systeme.io if they don't already exist."""
    if not settings.SYSTEMEIO_API_KEY:
        logger.warning("[DEV] No SYSTEMEIO_API_KEY — skipping contact seed")
        return

    import httpx
    headers = {"X-API-Key": settings.SYSTEMEIO_API_KEY, "Content-Type": "application/json"}
    base = settings.SYSTEMEIO_BASE_URL

    for contact in SEED_CONTACTS:
        try:
            with httpx.Client(timeout=10) as client:
                # Check if contact already exists
                r = client.get(f"{base}/contacts", params={"email": contact["email"]}, headers=headers)
                if r.status_code == 200 and r.json().get("items"):
                    logger.info("[DEV] systeme.io contact already exists: %s", contact["email"])
                    continue
                # Create contact
                r = client.post(f"{base}/contacts", json=contact, headers=headers)
                if r.status_code in (200, 201):
                    logger.warning("[DEV] Created systeme.io contact: %s %s <%s>",
                                   contact["firstName"], contact["lastName"], contact["email"])
                else:
                    logger.error("[DEV] Failed to create contact %s: %s %s",
                                 contact["email"], r.status_code, r.text)
        except Exception as exc:
            logger.error("[DEV] systeme.io seed error for %s: %s", contact["email"], exc)


def run_dev_startup(db: Session) -> None:
    if not settings.is_dev:
        return
    ensure_encryption_key()
    seed_default_admin(db)
    seed_systemeio_contacts()
