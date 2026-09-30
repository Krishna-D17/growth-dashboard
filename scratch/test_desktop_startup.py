import sys
from pathlib import Path

# Add backend directory
sys.path.insert(0, r"c:\Users\krish\Desktop\growth dashboard\backend")

from app.paths import app_paths
from app.config import settings
from app.desktop.postgres_manager import postgres_manager
from app.desktop.migration_manager import run_database_migrations

print("=== TESTING DESKTOP COMPONENT INITIALIZATION ===")
print("User data dir:", app_paths.user_data_dir)
print("Config dir:", app_paths.config_dir)
print("Data dir:", app_paths.data_dir)
print("Logs dir:", app_paths.logs_dir)
print("Exports dir:", app_paths.exports_dir)

app_paths.ensure_directories()

print("\n--- Postgres Manager Check ---")
print("Is port 5433 open?", postgres_manager.is_port_open())

print("\n--- Migration Manager Check ---")
alembic_ini = app_paths.get_alembic_ini()
print("Alembic ini path:", alembic_ini, "Exists?", alembic_ini.exists())
script_loc = app_paths.get_alembic_script_location()
print("Alembic script loc:", script_loc, "Exists?", script_loc.exists())

run_database_migrations()
print("Migrations executed successfully!")
