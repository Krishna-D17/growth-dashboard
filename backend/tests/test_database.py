from sqlalchemy import text
from app.database.session import engine, get_db


def test_database_connection():
    """Verify raw SQLAlchemy engine connection to PostgreSQL."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        scalar_val = result.scalar()
        assert scalar_val == 1


def test_database_session_dependency():
    """Verify FastAPI get_db session dependency yields a functional session."""
    db_gen = get_db()
    db_session = next(db_gen)
    try:
        result = db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        db_gen.close()
