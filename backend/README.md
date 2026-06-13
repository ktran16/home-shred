# HomeShred — Backend

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL.

## How to run (dev)

```bash
# from repo root: start postgres (dev DB is published on host port 5434)
docker compose up -d db

# from backend/
uv sync
cp .env.example .env            # adjust if needed
uv run alembic upgrade head                 # apply migrations
uv run python -m app.seed.seed_exercises    # seed exercises (idempotent)
uv run uvicorn app.main:app --reload --port 8000
```

> The dev DB is on host port **5434** (5432/5433 are used by other local
> containers). The test suite uses a separate `homeshred_test` database.

### Migrations

```bash
uv run alembic revision --autogenerate -m "message"   # generate (then review)
uv run alembic upgrade head                            # apply
```

API is served at `http://localhost:8000/api`. OpenAPI docs at `http://localhost:8000/docs`.
Health check: `curl http://localhost:8000/api/health` → `{"status":"ok"}`.

## Tests

```bash
uv run pytest
```

## Lint / format

```bash
uv run ruff check .
uv run ruff format .
```
