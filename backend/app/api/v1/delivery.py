from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.delivery_service import record_download

router = APIRouter(prefix="/delivery", tags=["Delivery"])


@router.get("/{token}")
def download_data(token: str, db: Session = Depends(get_db)):
    """Subject accesses their data via a secure download token."""
    delivery = record_download(token, db)
    if not delivery:
        raise HTTPException(status_code=404, detail="Download link not found or already used")
    if delivery.is_expired:
        raise HTTPException(
            status_code=410,
            detail="This download link has expired. Please submit a new request."
        )
    return JSONResponse({
        "message": "Download recorded. Your data has been logged as accessed.",
        "download_count": delivery.download_count,
        "method": delivery.delivery_method,
    })
