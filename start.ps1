# DataVerse DSAR — one-click local dev start (no Docker needed)
# Run from the dataversedsr folder: .\start.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "`n=== DataVerse DSAR Dev Startup ===" -ForegroundColor Cyan
Write-Host "No Docker required — runs on SQLite + local Python/Node`n" -ForegroundColor DarkGray

# ── 1. Create backend/.env if missing ────────────────────────────────────────
$envFile = Join-Path $backend ".env"
if (-not (Test-Path $envFile)) {
    @"
ENVIRONMENT=development
SECRET_KEY=dev-secret-key-change-me
DATABASE_URL=sqlite:///./dsar.db
REDIS_URL=redis://localhost:6379/0
RESEND_API_KEY=
EMAIL_FROM=onboarding@resend.dev
EMAIL_FROM_NAME=DataVerse DSAR
SYSTEMEIO_API_KEY=
ANTHROPIC_API_KEY=
ENCRYPTION_KEY=
"@ | Set-Content $envFile
    Write-Host "[OK] Created backend/.env with SQLite defaults" -ForegroundColor Green
} else {
    Write-Host "[OK] backend/.env already exists" -ForegroundColor Green
}

# ── 2. Install Python dependencies ───────────────────────────────────────────
Write-Host "`nInstalling Python packages..." -ForegroundColor Yellow
Set-Location $backend
python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip install failed." -ForegroundColor Red; exit 1
}
Write-Host "[OK] Python packages ready" -ForegroundColor Green

# ── 3. Install Node dependencies ─────────────────────────────────────────────
Write-Host "`nInstalling Node packages..." -ForegroundColor Yellow
Set-Location $frontend
npm install --silent
if ($LASTEXITCODE -ne 0) {
    Write-Host "npm install failed." -ForegroundColor Red; exit 1
}
Write-Host "[OK] Node packages ready" -ForegroundColor Green

# ── 4. Start backend in a new terminal window ────────────────────────────────
Write-Host "`nStarting backend (uvicorn)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$backend'; `$env:PYTHONIOENCODING='utf-8'; python -m uvicorn app.main:app --reload --port 8000"
) -WindowStyle Normal

# ── 5. Start frontend in a new terminal window ───────────────────────────────
Write-Host "Starting frontend (Vite)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$frontend'; npm run dev"
) -WindowStyle Normal

# ── 6. Wait for backend to be ready ──────────────────────────────────────────
Write-Host "`nWaiting for backend..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Write-Host "  ..." -ForegroundColor DarkGray
}

Set-Location $root

if (-not $ready) {
    Write-Host "`nBackend didn't respond in time — check the backend terminal for errors." -ForegroundColor Red
    exit 1
}

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host "`n=== All systems ready! ===" -ForegroundColor Green
Write-Host ""
Write-Host "  Subject portal  ->  http://localhost:3000/request/new" -ForegroundColor Cyan
Write-Host "  Admin queue     ->  http://localhost:3000/admin/queue" -ForegroundColor Cyan
Write-Host "  API docs        ->  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Admin login: admin@test.com / password123" -ForegroundColor Yellow
Write-Host "  (Created automatically — no manual setup needed)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  OTP code appears on-screen during testing — no email needed." -ForegroundColor DarkGray
Write-Host ""

Start-Process "http://localhost:3000/request/new"