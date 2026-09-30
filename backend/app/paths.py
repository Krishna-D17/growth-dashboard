import os
import sys
from pathlib import Path


def is_packaged() -> bool:
    """Check whether application is running inside a PyInstaller packaged executable."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_install_dir() -> Path:
    """Get the installation directory containing executable or main code."""
    if is_packaged():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_executable_dir() -> Path:
    """Get the directory containing the running executable file."""
    if is_packaged():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def get_user_data_dir() -> Path:
    """
    Get persistent per-user local app data directory.
    Default: %LOCALAPPDATA%\\SocialScope
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_dir = Path(local_app_data) / "SocialScope"
    else:
        base_dir = Path.home() / ".socialscope"
    return base_dir


class AppPaths:
    """Centralized path manager for SocialScope application."""

    def __init__(self):
        self.is_packaged = is_packaged()
        self.install_dir = get_install_dir()
        self.exe_dir = get_executable_dir()
        self.user_data_dir = get_user_data_dir()

        # Data & runtime directories
        self.config_dir = self.user_data_dir / "config"
        self.data_dir = self.user_data_dir / "data"
        self.postgres_data_dir = self.data_dir / "postgresql"
        self.logs_dir = self.user_data_dir / "logs"
        self.exports_dir = self.user_data_dir / "exports"
        self.backups_dir = self.user_data_dir / "backups"
        self.temp_dir = self.user_data_dir / "temp"

    def ensure_directories(self):
        """Create all required persistent user directories if they do not exist."""
        for d in [
            self.user_data_dir,
            self.config_dir,
            self.data_dir,
            self.postgres_data_dir,
            self.logs_dir,
            self.exports_dir,
            self.backups_dir,
            self.temp_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def get_alembic_ini(self) -> Path:
        """Get absolute path to alembic.ini."""
        return self.install_dir / "alembic.ini" if self.is_packaged else self.install_dir / "backend" / "alembic.ini"

    def get_alembic_script_location(self) -> Path:
        """Get absolute path to alembic script directory."""
        return self.install_dir / "alembic" if self.is_packaged else self.install_dir / "backend" / "alembic"

    def get_frontend_dist_dir(self) -> Path:
        """Get absolute path to static frontend build directory."""
        return self.install_dir / "frontend_dist" if self.is_packaged else self.install_dir / "frontend" / "dist"


app_paths = AppPaths()
