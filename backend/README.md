# Verbly AI — Backend Foundation

Backend foundation only. No product features are implemented yet
(AI Rewrite, Suggestions, Analytics, Location Intelligence, Auth). Those
are built in later, controlled stages on top of this base.

## Architecture

- Python 3.12, FastAPI
- Modular monolith, REST/JSON
- PostgreSQL via SQLAlchemy 2.0 (sync) + psycopg 3
- Alembic for migrations
- Pydantic v2 / pydantic-settings for configuration
- Flow: API → Service → Repository → Database

## 1. Python environment setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

## 2. Install dependencies

```bash
pip install -e ".[dev]"
```

This installs the app itself plus test dependencies (pytest, httpx).

## 3. Environment configuration

```bash
cp .env.example .env
```

Then edit `.env` and set real values (see "Environment variables" below).
`.env` is git-ignored and must never be committed.

## 4. Database configuration

You need a running PostgreSQL instance reachable at the connection string
in `DATABASE_URL`. For local development, any local PostgreSQL install or
a Docker container works, e.g.:

```bash
docker run --name verbly-postgres \
  -e POSTGRES_USER=verbly \
  -e POSTGRES_PASSWORD=verbly \
  -e POSTGRES_DB=verbly \
  -p 5432:5432 \
  -d postgres:16
```

Make sure `DATABASE_URL` in `.env` matches whatever instance you use.

## 5. Alembic

No application tables exist yet, so there is nothing to migrate. Once
models are added in a later stage:

```bash
# Generate a migration from model changes
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head
```

## 6. Running the API

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

## 7. Running tests

```bash
pytest
```

The `/health` test does not require a reachable PostgreSQL database.

## 8. Docker

```bash
docker build -t verbly-backend .
docker run --env-file .env -p 8000:8000 verbly-backend
```

## Project structure

```
backend/
├── app/
│   ├── api/            # FastAPI routers (endpoints)
│   ├── core/           # config, exception handling
│   ├── db/             # engine, session, declarative base
│   ├── models/         # SQLAlchemy models (empty for now)
│   ├── schemas/        # Pydantic schemas (empty for now)
│   ├── repositories/   # data-access layer (empty for now)
│   ├── services/       # business logic, incl. future ai/rewrite/etc
│   ├── utils/          # shared utilities
│   └── main.py         # FastAPI app entry point
├── tests/
├── alembic/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```
