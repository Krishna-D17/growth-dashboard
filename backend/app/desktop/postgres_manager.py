import os
import sys
import time
import socket
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from app.paths import app_paths


class PostgresManager:
    """
    Application-managed local PostgreSQL service manager.
    Controls local PostgreSQL binaries, initdb, startup, database creation, and clean shutdown.
    Ensures persistent database storage under LocalAppData.
    """

    def __init__(self, port: int = 5433, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.db_name = "socialscope"
        self.user = "socialscope"
        self.password = "socialscope"
        self.pg_data_dir = app_paths.postgres_data_dir

    def get_pg_binary_info(self, binary_name: str) -> tuple[Optional[Path], str]:
        """Find executable binary and return (Path, source) where source is 'bundled' or 'system'."""
        # 1. Bundled in install_dir/postgres/bin
        bundled_bin = app_paths.install_dir / "postgres" / "bin" / f"{binary_name}.exe"
        if bundled_bin.exists():
            return (bundled_bin, "bundled")

        bundled_bin_exe = app_paths.exe_dir / "postgres" / "bin" / f"{binary_name}.exe"
        if bundled_bin_exe.exists():
            return (bundled_bin_exe, "bundled")

        # In packaged mode, strictly require bundled PostgreSQL
        if app_paths.is_packaged:
            return (None, "missing")

        # 2. System PATH (development mode fallback)
        system_bin = shutil.which(binary_name)
        if system_bin:
            return (Path(system_bin), "system")

        # 3. Standard Windows PostgreSQL install paths (development mode fallback)
        pg_program_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "PostgreSQL"
        if pg_program_files.exists():
            for ver_dir in sorted(pg_program_files.glob("*"), reverse=True):
                bin_path = ver_dir / "bin" / f"{binary_name}.exe"
                if bin_path.exists():
                    return (bin_path, "system")

        return (None, "missing")

    def find_pg_binary(self, binary_name: str) -> Optional[Path]:
        """Find executable binary in bundled directory or system location."""
        path, _ = self.get_pg_binary_info(binary_name)
        return path

    def is_port_open(self) -> bool:
        """Check if localhost port is listening and accepting TCP connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            result = sock.connect_ex((self.host, self.port))
            return result == 0

    def check_readiness_detail(self) -> tuple[bool, str]:
        """
        Detailed check of PostgreSQL readiness.
        Returns (True, "Ready: SELECT 1 succeeded") or (False, "Transient error: the database system is starting up").
        """
        import psycopg

        # 1. Try pg_isready if available
        pg_isready_bin = self.find_pg_binary("pg_isready")
        if pg_isready_bin:
            cmd = [str(pg_isready_bin), "-h", self.host, "-p", str(self.port)]
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2, creationflags=creationflags)
                if res.returncode != 0:
                    return (False, f"pg_isready reported not ready (exit code {res.returncode}): {res.stdout.strip() or res.stderr.strip()}")
            except Exception:
                pass

        # 2. Try direct psycopg connection test
        for dsn in [
            f"postgresql://postgres@{self.host}:{self.port}/postgres",
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}",
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/postgres",
        ]:
            try:
                with psycopg.connect(dsn, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        cur.fetchone()
                    return (True, f"Database connection test succeeded on DSN: {dsn.split('@')[-1]}")
            except psycopg.OperationalError as op_err:
                err_msg = str(op_err).strip()
                return (False, f"OperationalError during startup: {err_msg}")
            except Exception as ex:
                err_msg = str(ex).strip()
                if "starting up" in err_msg.lower() or "connection refused" in err_msg.lower():
                    return (False, f"Transient startup error: {err_msg}")
                if "database" in err_msg.lower() and "does not exist" in err_msg.lower():
                    return (True, "PostgreSQL engine ready (database socialscope pending creation)")

        return (False, "Port not accepting TCP connections yet")

    def is_db_ready(self) -> bool:
        """Check if PostgreSQL engine is ready and accepting SQL queries."""
        is_ready, _ = self.check_readiness_detail()
        return is_ready

    def wait_for_readiness(self, timeout_seconds: int = 60, poll_interval: float = 0.5, log_callback=None) -> bool:
        """
        Poll PostgreSQL server until it is fully ready to accept database connections.
        Specifically tolerates transient startup states like 'the database system is starting up'.
        Returns True if ready within timeout_seconds, raises RuntimeError on timeout.
        """
        start_time = time.time()
        last_log_time = 0

        while time.time() - start_time < timeout_seconds:
            is_ready, detail = self.check_readiness_detail()
            if is_ready:
                if log_callback:
                    log_callback("[9] PostgreSQL readiness check", f"PostgreSQL is ready and accepting connections ({detail})")
                return True

            now = time.time()
            if now - last_log_time >= 5:
                if log_callback:
                    log_callback("[9] PostgreSQL readiness check", f"Waiting for PostgreSQL readiness... ({detail})")
                last_log_time = now

            time.sleep(poll_interval)

        raise RuntimeError(f"PostgreSQL server failed to become ready on {self.host}:{self.port} within {timeout_seconds} seconds.")

    def init_database_cluster(self):
        """Initialize PostgreSQL data directory using initdb if PG_VERSION is missing."""
        version_file = self.pg_data_dir / "PG_VERSION"
        if version_file.exists():
            return

        initdb_bin = self.find_pg_binary("initdb")
        if not initdb_bin:
            raise RuntimeError("PostgreSQL 'initdb' binary not found. Please install PostgreSQL or bundle binaries.")

        print(f"[PostgresManager] Initializing new database cluster at {self.pg_data_dir}...")
        cmd = [
            str(initdb_bin),
            "-U", "postgres",
            "-A", "trust",
            "-E", "UTF8",
            "--pgdata=" + str(self.pg_data_dir)
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creationflags)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to initialize PostgreSQL database cluster: {res.stderr}")

    def start_server(self, log_callback=None):
        """Start local PostgreSQL server process on configured localhost port and wait for readiness."""
        if self.is_db_ready():
            if log_callback:
                log_callback("[8] PostgreSQL process check", f"PostgreSQL is already running and ready on {self.host}:{self.port}")
            print(f"[PostgresManager] PostgreSQL is already running and ready on {self.host}:{self.port}")
            return

        # If port is open but DB is not ready yet (e.g. process starting up), skip spawning new process
        if not self.is_port_open():
            pg_ctl_bin = self.find_pg_binary("pg_ctl")
            postgres_bin = self.find_pg_binary("postgres")
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            log_file = app_paths.logs_dir / "postgres.log"

            if pg_ctl_bin:
                cmd = [
                    str(pg_ctl_bin),
                    "start",
                    "-D", str(self.pg_data_dir),
                    "-l", str(log_file),
                    "-o", f"-p {self.port} -h {self.host}"
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
            elif postgres_bin:
                with open(log_file, "a") as f:
                    subprocess.Popen(
                        [str(postgres_bin), "-D", str(self.pg_data_dir), "-p", str(self.port), "-h", self.host],
                        stdout=f,
                        stderr=f,
                        creationflags=creationflags
                    )
            else:
                raise RuntimeError("Neither 'pg_ctl' nor 'postgres' binary was found.")

        # Wait for actual database readiness
        self.wait_for_readiness(timeout_seconds=60, poll_interval=0.5, log_callback=log_callback)

    def ensure_database_and_user(self):
        """Verify and create socialscope database and user if missing using psycopg."""
        import psycopg

        # 1. First test if target database and user already exist and accept connections
        try:
            target_dsn = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
            with psycopg.connect(target_dsn, connect_timeout=3) as conn:
                return
        except Exception:
            pass

        # 2. Connect as postgres superuser to create user and database
        try:
            admin_dsn = f"postgresql://postgres@{self.host}:{self.port}/postgres"
            with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname = '{self.user}'")
                    if not cur.fetchone():
                        cur.execute(f"CREATE ROLE {self.user} WITH LOGIN PASSWORD '{self.password}' SUPERUSER")
                    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.db_name}'")
                    if not cur.fetchone():
                        cur.execute(f"CREATE DATABASE {self.db_name} OWNER {self.user}")
        except Exception as e:
            print(f"[PostgresManager] User/Database creation notice: {e}")

    def stop_server(self):
        """Cleanly stop local PostgreSQL server."""
        pg_ctl_bin = self.find_pg_binary("pg_ctl")
        if pg_ctl_bin and self.is_port_open():
            print("[PostgresManager] Stopping local PostgreSQL server...")
            cmd = [str(pg_ctl_bin), "stop", "-D", str(self.pg_data_dir), "-m", "fast"]
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creationflags)


postgres_manager = PostgresManager()
