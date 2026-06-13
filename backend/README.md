# HomeShred — Backend

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL.

## How to run (dev)

```bash
# from repo root: start postgres
docker compose up -d db

# from backend/
uv sync
cp .env.example .env            # adjust if needed
uv run uvicorn app.main:app --reload --port 8000
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
