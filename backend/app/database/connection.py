"""
Database engine + session management.

Exposes:
- `engine`   : the SQLAlchemy engine, built from DATABASE_URL
- `SessionLocal` : session factory used to create per-request DB sessions
- `get_db()` : FastAPI dependency that yields a session and guarantees
               it's closed after the request, even on error
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # avoids "server closed the connection" errors on idle connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency — provides a scoped DB session per request.
    Usage: `db: Session = Depends(get_db)`
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
