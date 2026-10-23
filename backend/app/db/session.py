"""SQLAlchemy engine/session setup.

Works unmodified against SQLite (the zero-setup local default) or
PostgreSQL (production target) — the only difference is `DATABASE_URL`.
See .env.example.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLite needs this connect_arg when used from multiple threads (FastAPI's
# default dev server uses a thread pool). It's a no-op for PostgreSQL.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """FastAPI dependency yielding a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
