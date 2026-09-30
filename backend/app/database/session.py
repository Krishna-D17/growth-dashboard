from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Initialize SQLAlchemy 2.x engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False
)

# Session factory for database operations
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional database session per request.
    Safely closes the session when request lifecycle completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
