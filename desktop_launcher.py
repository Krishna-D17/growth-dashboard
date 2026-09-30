import os
import sys
import time
import signal
import socket
import hashlib
import traceback
import webbrowser
import threading
import urllib.request
import urllib.error
from pathlib import Path

# Safe stdout/stderr redirection for windowed consoleless executable mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Setup initial path resolution for PyInstaller vs Source execution
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    meipass = getattr(sys, "_MEIPASS")
    if meipass not in sys.path:
        sys.path.insert(0, meipass)
else:
    backend_dir = Path(__file__).resolve().parent / "backend"
    if backend_dir.exists() and str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of executable file."""
    try:
        if not filepath.exists() or not filepath.is_file():
            return "N/A"
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "ERROR_COMPUTING"


def log_startup(stage: str, details: str = "", is_error: bool = False, exc: Exception = None):
    """Write structured timestamped startup event to LocalAppData/SocialScope/logs/startup.log and stdout."""
    local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home()))
    log_dir = Path(local_app_data) / "SocialScope" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "startup.log"
    except Exception:
        log_file = None

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status = "FAILED" if is_error else "OK"
    message = f"[{timestamp}] [{status}] {stage}"
    if details:
        message += f" - {details}"
    message += "\n"

    if exc or is_error:
        tb_str = traceback.format_exc()
        if tb_str and tb_str.strip() != "NoneType: None":
            message += f"FULL TRACEBACK:\n{tb_str}\n"

    try:
        print(message, end="", flush=True)
    except Exception:
        pass

    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(message)
        except Exception:
            pass


def show_error_dialog(title: str, message: str):
    """Show native Windows message box dialog if running on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home()))
            log_path = Path(local_app_data) / "SocialScope" / "logs" / "startup.log"
            full_msg = f"{message}\n\nSee detailed log at:\n{log_path}"
            ctypes.windll.user32.MessageBoxW(0, full_msg, title, 0x10)  # MB_ICONERROR
        except Exception:
            pass


# Top-level import section with startup logging
try:
    exe_path = Path(sys.executable).resolve()
    exe_hash = compute_file_sha256(exe_path)
    is_frozen = getattr(sys, 'frozen', False)
    meipass_path = getattr(sys, '_MEIPASS', 'N/A')
    cwd_path = Path.cwd()

    log_startup(
        "[1] launcher started",
        f"exe_path={exe_path}, exe_sha256={exe_hash}, frozen={is_frozen}, meipass={meipass_path}, cwd={cwd_path}, python={sys.version.split()[0]}"
    )

    from app.paths import app_paths
    log_startup("[2] runtime paths resolved", f"install_dir={app_paths.install_dir}, exe_dir={app_paths.exe_dir}, user_data_dir={app_paths.user_data_dir}")

    from app.config import settings
    log_startup("[3] configuration loaded", f"backend_host={settings.backend_host}, backend_port={settings.backend_port}, db_configured=YES, ai_provider={settings.ai_provider}, browser_headless={settings.browser_headless}")

    from app.desktop.postgres_manager import postgres_manager
    log_startup("[5] PostgreSQL manager loaded")

    from app.desktop.migration_manager import run_database_migrations
    log_startup("[11] Alembic migration manager loaded")

except Exception as e:
    log_startup("CRITICAL INITIALIZATION ERROR", "Failed to import application modules", is_error=True, exc=e)
    show_error_dialog("SocialScope Startup Failure", f"Failed to initialize application modules: {e}")
    sys.exit(1)


LOCK_FILE = app_paths.temp_dir / "socialscope.lock"
server_instance = None
running = True


def wait_for_backend_health(host: str, port: int, timeout_seconds: int = 30) -> bool:
    health_url = f"http://{host}:{port}/health"
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass
        time.sleep(0.5)
    return False


def acquire_single_instance_lock() -> bool:
    """Ensure only one instance of SocialScope runs at a time using backend health verification."""
    # First check if backend server is ALIVE on configured port
    if wait_for_backend_health(settings.backend_host, settings.backend_port, timeout_seconds=1):
        log_startup("[4] single-instance check", f"Active SocialScope server detected listening on {settings.backend_host}:{settings.backend_port}.")
        return False

    # If backend is NOT listening, any existing lock file is stale and must be cleared
    if LOCK_FILE.exists():
        try:
            stale_pid = LOCK_FILE.read_text().strip()
            log_startup("[4] single-instance check", f"Clearing stale lock file (previous PID {stale_pid}).")
            LOCK_FILE.unlink()
        except Exception:
            pass

    try:
        LOCK_FILE.write_text(str(os.getpid()))
        log_startup("[4] single-instance check", f"Lock acquired (PID {os.getpid()})")
        return True
    except Exception as e:
        log_startup("[4] single-instance check notice", f"Could not write lock file: {e}")
        return True


def release_single_instance_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def start_uvicorn_server():
    try:
        log_startup("[13] FastAPI import", "Importing app.main...")
        import uvicorn
        from app.main import app
        log_startup("[14] Uvicorn startup", f"Starting server on {settings.backend_host}:{settings.backend_port}")

        config = uvicorn.Config(
            app=app,
            host=settings.backend_host,
            port=settings.backend_port,
            log_level="info",
            access_log=True,
        )
        global server_instance
        server_instance = uvicorn.Server(config)
        server_instance.install_signal_handlers = lambda: None
        server_instance.run()
    except Exception as e:
        log_startup("[14] Uvicorn startup", "Failed to start Uvicorn server", is_error=True, exc=e)
        show_error_dialog("SocialScope Server Error", f"Uvicorn server failed: {e}")


def shutdown_application(signum=None, frame=None):
    global running, server_instance
    if not running:
        return
    running = False

    log_startup("SHUTDOWN", "Initiating graceful application shutdown...")
    if server_instance:
        server_instance.should_exit = True

    try:
        postgres_manager.stop_server()
    except Exception as e:
        log_startup("SHUTDOWN", f"Error stopping PostgreSQL: {e}", is_error=True, exc=e)

    release_single_instance_lock()
    log_startup("SHUTDOWN", "Shutdown complete. Exiting.")
    sys.exit(0)


def main():
    try:
        app_paths.ensure_directories()
        signal.signal(signal.SIGINT, shutdown_application)
        signal.signal(signal.SIGTERM, shutdown_application)

        if not acquire_single_instance_lock():
            dashboard_url = f"http://{settings.backend_host}:{settings.backend_port}/"
            log_startup("[17] browser launch", f"Focusing existing dashboard at {dashboard_url}")
            try:
                webbrowser.open(dashboard_url)
            except Exception:
                pass
            sys.exit(0)

        # 5. PostgreSQL Binaries & Data Directory
        pg_bin, pg_source = postgres_manager.get_pg_binary_info("initdb")
        if not pg_bin:
            pg_bin, pg_source = postgres_manager.get_pg_binary_info("postgres")

        log_startup("[5] PostgreSQL binaries located", f"path={pg_bin}, postgres_source={pg_source}")
        if not pg_bin:
            raise RuntimeError("PostgreSQL binaries not found! Bundled PostgreSQL is required.")

        log_startup("[6] PostgreSQL data directory located/created", f"dir={postgres_manager.pg_data_dir}")

        # 7. PostgreSQL Initialization
        log_startup("[7] PostgreSQL initialization", "Checking/initializing cluster...")
        postgres_manager.init_database_cluster()

        # 8. PostgreSQL Process Startup & Readiness Wait
        log_startup("[8] PostgreSQL process startup", f"Starting server on port {postgres_manager.port}...")
        postgres_manager.start_server(log_callback=log_startup)

        # 9. Readiness & DB/User setup
        log_startup("[9] PostgreSQL readiness confirmed", "Engine is ready to accept connections")
        log_startup("[10] database connection", "Verifying socialscope database and user...")
        postgres_manager.ensure_database_and_user()

        # 12. Alembic Migrations
        log_startup("[12] Alembic migration execution", "Running migrations to head...")
        run_database_migrations()

        # 13. Start FastAPI Server
        server_thread = threading.Thread(target=start_uvicorn_server, daemon=True)
        server_thread.start()

        # 15. Health Check
        log_startup("[15] /health check", "Waiting for http://127.0.0.1:8000/health...")
        if not wait_for_backend_health(settings.backend_host, settings.backend_port, timeout_seconds=30):
            raise RuntimeError("Backend health check timed out after 30 seconds.")

        log_startup("[15] /health check", "HEALTH OK (200 OK)")

        # 16. Frontend Static Files
        frontend_dist = app_paths.get_frontend_dist_dir()
        log_startup("[16] frontend static files located", f"dist_dir={frontend_dist}, exists={frontend_dist.exists()}")

        # 17. Browser Launch
        dashboard_url = f"http://{settings.backend_host}:{settings.backend_port}/"
        log_startup("[17] browser launch", f"Opening dashboard at {dashboard_url}")
        browser_opened = False
        try:
            browser_opened = webbrowser.open(dashboard_url)
            if not browser_opened and sys.platform == "win32":
                os.startfile(dashboard_url)
                browser_opened = True
        except Exception as b_err:
            log_startup("[17] browser launch notice", f"Auto browser launch notice: {b_err}")

        if not browser_opened:
            log_startup("[17] browser launch notice", f"Dashboard available manually at {dashboard_url}")

        log_startup("[18] startup complete", "SocialScope is running successfully.")

        while running:
            time.sleep(1.0)

    except Exception as e:
        log_startup("STARTUP FAILURE", f"Application launch aborted: {e}", is_error=True, exc=e)
        show_error_dialog("SocialScope Startup Error", f"SocialScope could not start.\n\nError: {e}")
        shutdown_application()


if __name__ == "__main__":
    main()
