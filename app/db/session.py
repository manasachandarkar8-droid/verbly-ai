"""
Database engine/session setup (foundation layer).

Uses synchronous SQLAlchemy 2.0 with the psycopg 3 driver, per the
project's established architecture. The engine is created lazily (no
connection is opened at import time), so importing this module is safe
even when no database is reachable -- which matters for Feature 1's test
suite, since Feature 1 itself never touches the database.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
