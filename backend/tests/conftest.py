"""
Shared pytest fixtures.

Sets a placeholder DATABASE_URL before the app is imported so that
Settings() validation succeeds without requiring a real, reachable
PostgreSQL instance. Nothing in the /health endpoint (or app startup)
actually opens a database connection, so this is safe for the test suite
at this stage.
"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)
