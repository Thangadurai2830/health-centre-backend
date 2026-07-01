# SwasthyaSetu Backend (FastAPI)

Production-structured FastAPI service: async SQLAlchemy + PostgreSQL, Alembic migrations, JWT auth, layered architecture.

## Layout

```
app/
  api/v1/endpoints/   route handlers
  api/deps.py          shared dependencies (DB session, current user)
  core/                config, security, logging, exceptions
  db/                  engine/session, declarative base
  models/              SQLAlchemy ORM models
  schemas/             Pydantic request/response schemas
  services/            business logic, called by endpoints
  middleware/          request-id, error handling
  main.py              app factory + entrypoint
alembic/               DB migrations
tests/                 pytest suite (mirrors app/ layout)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # edit SECRET_KEY, DATABASE_URL, etc.
```

## Run

```bash
uvicorn app.main:app --reload
```

Docs at `/docs` (disabled in production).

## Migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## Tests

```bash
pytest
```

## Docker

```bash
docker compose up --build
```
