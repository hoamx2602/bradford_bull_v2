"""SQLAlchemy engine/session setup.

SQLite today; point DB_URL at Postgres later and nothing else changes. The
session factory and Base are the only things the rest of the app imports.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

# check_same_thread=False lets the in-process worker thread share the SQLite
# engine. For Postgres this connect_arg is simply ignored.
_connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}

engine = create_engine(settings.db_url, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables and ensure storage dir exists. Idempotent."""
    # Import models so they register on Base.metadata before create_all.
    from app.db import models  # noqa: F401

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir.parent).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator:
    """Transactional session for worker/background code."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator:
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
