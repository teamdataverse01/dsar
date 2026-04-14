from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.schemas.auth import LoginRequest, TokenResponse, AdminUserOut
from app.api.deps import get_current_admin

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter_by(email=body.email.lower()).first()
    if not admin or not verify_password(body.password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    admin.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": admin.id, "email": admin.email})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AdminUserOut)
def get_me(admin: AdminUser = Depends(get_current_admin)):
    return admin


@router.post("/seed-admin", include_in_schema=False)
def seed_admin(email: str, password: str, full_name: str, db: Session = Depends(get_db)):
    """Dev-only endpoint to create the first admin user."""
    from app.core.config import settings
    if not settings.is_dev:
        raise HTTPException(status_code=403, detail="Only available in development")
    existing = db.query(AdminUser).filter_by(email=email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")
    admin = AdminUser(
        email=email.lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        is_superadmin=True,
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin created", "email": email}
