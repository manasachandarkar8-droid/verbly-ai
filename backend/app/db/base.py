"""
SQLAlchemy 2.0 declarative base (foundation layer).

Feature 1 (web scraping / content extraction) is stateless and does not
persist anything, so no models are defined here yet. This exists so later
features have a consistent base class to import, and so Alembic has a
target metadata object to autogenerate against.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
