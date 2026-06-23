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

    # Lightweight dev migration: create_all never alters existing tables, so
    # add columns introduced after a DB was first created. No-op when present.
    with engine.connect() as conn:
        for ddl in (
            "ALTER TABLE jobs ADD COLUMN kit VARCHAR(16) DEFAULT 'away'",
            "ALTER TABLE jobs ADD COLUMN team_refs_key VARCHAR(512)",
            "ALTER TABLE analyses ADD COLUMN teamdet_key VARCHAR(512)",
            "ALTER TABLE analyses ADD COLUMN facts_json JSON",
        ):
            try:
                conn.exec_driver_sql(ddl)
                conn.commit()
            except Exception:
                pass

    _seed_defaults()


# Default kit-placement taxonomy from the customer's "Highlight Video" sheet.
# (location_id, name, anchor_id, brand_key, human_percentage). anchor_id maps to
# the nearest computable pose anchor in bodyzones.ZONE_IDS; close neck/back slots
# intentionally share an anchor (COCO-17 can't separate them) — tune in Settings.
_SEED_LOCATIONS: list[tuple[str, str, str, str | None, float]] = [
    ("main-sponsor",     "Main Sponsor",      "chest-center",   "top_notch",        26.0),
    ("collar-back",      "Collar Back",       "back-top",       None,                8.0),
    ("collar-bone",      "Collar Bone",       "chest-l",        "mna_cladding",      8.0),
    ("chest-opp-badge",  "Chest (opp Badge)", "chest-r",        "romatica",          7.0),
    ("sleeve-1",         "Sleeve 1",          "sleeve-l",       None,                4.0),
    ("sleeve-2",         "Sleeve 2",          "sleeve-r",       "atm",              11.0),
    ("sleeve-3",         "Sleeve 3",          "shoulder-l",     "bartercard",        4.0),
    ("top-back",         "Top Back",          "back-top",       "mcp",               5.0),
    ("nape-neck",        "Nape Neck",         "back-top",       "fairway",           3.0),
    ("bottom-back",      "Bottom Back",       "back-lower",     "asc_group",         3.0),
    ("top-back-shorts",  "Top Back Shorts",   "shorts-back",    "klg",               5.0),
    ("shorts-front",     "Shorts Front",      "shorts-front-l", None,                3.0),
    ("shorts-back-1",    "Shorts Back 1",     "shorts-leg-l",   "aon",               3.0),
    ("shorts-back-2",    "Shorts Back 2",     "shorts-leg-r",   "paints_lacquers",   3.0),
    ("socks-front",      "Socks front",       "sock-l",         "ellgren",           1.0),
    ("socks-back",       "Socks back",        "sock-r",         "em_workwear",     100.0),
]

# All Tier-1..3 algorithm factors enabled by default (matches the legacy
# visibility = size·position·clarity·obb behaviour, plus duration weighting).
_DEFAULT_AI_CRITERIA: list[str] = ["size", "position", "clarity", "obb", "durationWeight"]


def _seed_defaults() -> None:
    """Populate LocationConfig + the ai_criteria setting on first run only."""
    from app.db.models import AppSetting, LocationConfig

    with SessionLocal() as s:
        if s.get(LocationConfig, "main-sponsor") is None:
            for i, (lid, name, anchor, brand, human) in enumerate(_SEED_LOCATIONS):
                s.add(LocationConfig(
                    id=lid, name=name, order_index=i, anchor_id=anchor,
                    brand_key=brand, human_percentage=human,
                ))
        if s.get(AppSetting, "ai_criteria") is None:
            s.add(AppSetting(key="ai_criteria", value={"enabled": _DEFAULT_AI_CRITERIA}))
        s.commit()


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
