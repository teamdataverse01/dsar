# DataVerse DSAR Pilot — Dev Setup

## Prerequisites
- Docker Desktop
- Python 3.11+ (for running backend locally without Docker)
- Node.js 20+ (for running frontend locally without Docker)

---

## Option A — Docker Compose (recommended)

```bash
# 1. From the project root
cd dataversedsr

# 2. Start everything
docker compose up --build

# 3. Backend API:   http://localhost:8000
#    Frontend:      http://localhost:3000
#    API docs:      http://localhost:8000/docs
```

---

## Option B — Local (no Docker)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis separately (Docker is easiest):
docker run -d -p 5432:5432 -e POSTGRES_USER=dsar_user -e POSTGRES_PASSWORD=dsar_pass -e POSTGRES_DB=dsar_db postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Generate encryption key and add to .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste output as ENCRYPTION_KEY in backend/.env

# Run migrations
alembic upgrade head

# Create your first admin user (dev only)
uvicorn app.main:app --reload &
curl -X POST "http://localhost:8000/api/v1/auth/seed-admin?email=admin@dataverse.com&password=changeme&full_name=Admin"

# Start API server
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

---

## First login

1. Go to `http://localhost:3000/admin/login`
2. Email: `admin@dataverse.com`
3. Password: `changeme`

---

## Testing the full flow

1. Open `http://localhost:3000/request/new`
2. Fill in a **subject email that exists in your systeme.io account**
3. Select request type: **Access** or **Deletion**
4. Submit — you'll receive an OTP email (or see it in terminal in dev mode)
5. Enter the OTP at `/request/verify/{id}`
6. Check status at `/request/status/{reference}`
7. In the admin queue at `/admin/queue`, click the request
8. Click **Advance Workflow** → runs the systeme.io lookup
9. Run **QA Check** → confirm all pass
10. Click **Generate Draft** → review AI draft if configured
11. Click **Deliver via Email** → sends response to subject

---

## Environment variables

All documented in `backend/.env`. Key ones:

| Variable | Purpose |
|---|---|
| `RESEND_API_KEY` | Email sending (OTPs, notifications) |
| `SYSTEMEIO_API_KEY` | systeme.io API connector |
| `ENCRYPTION_KEY` | Fernet key for data package encryption |
| `SECRET_KEY` | JWT signing key — change before any demo |
| `ANTHROPIC_API_KEY` | Optional — AI draft generation |

---

## Project structure

```
dataversedsr/
├── backend/
│   ├── app/
│   │   ├── core/          config, database, security, logging
│   │   ├── models/        8 SQLAlchemy ORM models
│   │   ├── schemas/       Pydantic schemas
│   │   ├── api/v1/        intake, admin, auth, delivery routes
│   │   ├── services/      10 business logic services
│   │   ├── workers/       Celery tasks
│   │   └── templates/     8 response templates
│   └── migrations/        Alembic
└── frontend/
    └── src/
        ├── pages/         IntakeForm, Verification, Status, AdminQueue, AdminRequestDetail
        └── services/      API client
```
