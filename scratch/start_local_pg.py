import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.desktop.postgres_manager import postgres_manager

print("Checking PostgreSQL engine status...")
if postgres_manager.is_db_ready():
    print("PostgreSQL is running and READY.")
else:
    print("PostgreSQL is stopped/not ready. Starting server...")
    postgres_manager.start_server(log_callback=lambda s, d: print(f"[{s}] {d}"))
    print("PostgreSQL server started successfully.")
