"""
Week 2: Database session management for FastAPI.

Provides:
- engine (SQLite)
- SessionLocal (scoped session)
- get_db() dependency for FastAPI
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base


def _default_sqlite_url() -> str:
    backend_dir = Path(__file__).resolve().parents[2]  # backend/
    db_path = (backend_dir / "data_lake.db").resolve()
    # SQLAlchemy expects forward slashes in sqlite URLs on Windows.
    return f"sqlite:///{db_path.as_posix()}"


# Can be overridden for tests / deployments (e.g. "sqlite:///:memory:" or Postgres).
DB_URL = os.getenv("DB_URL", _default_sqlite_url())

# Ensure backend/ is in path
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},  # SQLite threading
    echo=False,  # Set True for SQL logging
)

# Dependency
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    FastAPI dependency to get DB session.
    
    Usage:
        @app.get("/files")
        def get_files(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    print(f"DB initialized: {DB_URL}")


if __name__ == "__main__":
    # Test DB creation
    init_db()
