import os
import sys
from alembic.config import Config
from alembic import command
from app.paths import app_paths
from app.config import settings


def run_database_migrations():
    """
    Programmatically execute Alembic migrations to reach head revision.
    Works seamlessly in both development and PyInstaller packaged modes.
    """
    alembic_ini_path = app_paths.get_alembic_ini()
    script_location = app_paths.get_alembic_script_location()

    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"Alembic config file not found at {alembic_ini_path}")

    print(f"[MigrationManager] Running Alembic migrations using config: {alembic_ini_path}")
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(script_location))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    # Execute Alembic upgrade head
    command.upgrade(alembic_cfg, "head")
    print("[MigrationManager] Alembic database migration completed successfully.")
