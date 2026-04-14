"""
DataVerse DSAR — double-click start.py to launch the app.
Kills any old backend/frontend processes, starts fresh, opens browser.
"""
import os
import sys
import time
import signal
import subprocess
import urllib.request
from pathlib import Path

ROOT    = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

def kill_existing():
    """Kill any process already using ports 8000, 5173, or 3000."""
    print("[*] Killing any existing backend/frontend processes...")
    my_pid = str(os.getpid())
    for port in [8000, 5173, 3000]:
        try:
            out = subprocess.check_output(
                f'netstat -ano | findstr ":{port} "',
                shell=True, stderr=subprocess.DEVNULL
            ).decode()
            pids = set()
            for line in out.splitlines():
                parts = line.strip().split()
                if parts and parts[-1].isdigit() and parts[-1] != my_pid:
                    pids.add(parts[-1])
            for pid in pids:
                subprocess.call(
                    f"taskkill /F /PID {pid}",
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        except Exception:
            pass
    time.sleep(1)
    print("[OK] Cleared old processes")

def ensure_env():
    env_file = BACKEND / ".env"
    if not env_file.exists():
        env_file.write_text("""\
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
""")
        print("[OK] Created backend/.env")
    else:
        print("[OK] backend/.env exists")

def install_deps():
    print("[*] Installing Python packages...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        cwd=BACKEND, check=True
    )
    print("[OK] Python packages ready")

    print("[*] Installing Node packages...")
    subprocess.run("npm install --silent", cwd=FRONTEND, shell=True, check=True)
    print("[OK] Node packages ready")

def start_backend():
    print("[*] Starting backend...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND,
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,  # Windows: new window
    )
    return proc

def start_frontend():
    print("[*] Starting frontend...")
    proc = subprocess.Popen(
        "npm run dev",
        cwd=FRONTEND,
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    return proc

def wait_for_url(url, label, timeout=60):
    print(f"[*] Waiting for {label}", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            print(" ready!")
            return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(2)
    print(f"\n[ERROR] {label} did not start in time — check its console window.")
    return False

def open_browser():
    import webbrowser
    webbrowser.open("http://localhost:3000/request/new")

if __name__ == "__main__":
    print("\n=== DataVerse DSAR Dev Startup ===\n")
    kill_existing()
    ensure_env()
    install_deps()
    start_backend()
    start_frontend()
    backend_ok  = wait_for_url("http://localhost:8000/health", "backend (port 8000)")
    frontend_ok = wait_for_url("http://localhost:3000", "frontend (port 3000)")
    if backend_ok and frontend_ok:
        print("\n=== All systems ready! ===")
        print("  Subject portal  ->  http://localhost:3000/request/new")
        print("  Admin panel     ->  http://localhost:3000/admin/queue")
        print("  API docs        ->  http://localhost:8000/docs")
        print("  Admin login     ->  admin@test.com / password123")
        print("  OTP shown on-screen during testing.\n")
        open_browser()
        print("Press Ctrl+C or close this window to stop.\n")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nShutting down...")
