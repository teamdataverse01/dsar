from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import Base, engine, SessionLocal
from app.core.startup import run_dev_startup
from app.api.v1 import intake, admin, auth, delivery

setup_logging()

# Auto-create tables (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: seed dev defaults so no manual setup is needed
    db = SessionLocal()
    try:
        run_dev_startup(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="DataVerse DSAR Management System — Pilot",
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(intake.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(delivery.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}
