import psycopg
from psycopg import sql

def test_db_init():
    try:
        # Try connecting with socialscope user
        conn = psycopg.connect("postgresql://socialscope:socialscope@127.0.0.1:5433/socialscope", connect_timeout=5)
        print("Connected as socialscope user to socialscope DB!")
        conn.close()
        return
    except Exception as e:
        print("socialscope connection failed:", e)

    # Try connecting as postgres user
    try:
        conn = psycopg.connect("postgresql://postgres@127.0.0.1:5433/postgres", autocommit=True, connect_timeout=5)
        print("Connected as postgres user!")
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'socialscope'")
            if not cur.fetchone():
                print("Creating role socialscope...")
                cur.execute("CREATE ROLE socialscope WITH LOGIN PASSWORD 'socialscope' SUPERUSER")
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'socialscope'")
            if not cur.fetchone():
                print("Creating database socialscope...")
                cur.execute("CREATE DATABASE socialscope OWNER socialscope")
        conn.close()
        print("Database & user setup complete via psycopg!")
    except Exception as e:
        print("postgres connection failed:", e)

if __name__ == "__main__":
    test_db_init()
