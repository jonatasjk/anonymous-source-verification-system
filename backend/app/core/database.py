from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

import redis as redis_lib

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# PostgreSQL (sync — used by both FastAPI and Celery workers)
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for use in Celery tasks and service helpers."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
_redis_client: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def set_submission_status(submission_id: str, status: str) -> None:
    get_redis().set(f"submission:{submission_id}:status", status, ex=86400)


def get_submission_status(submission_id: str) -> str | None:
    return get_redis().get(f"submission:{submission_id}:status")
