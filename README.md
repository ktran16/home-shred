# HomeShred

A self-hosted, rule-based personal-trainer web app for home calisthenics + dumbbell
training (muscle gain + fat loss). FastAPI + PostgreSQL backend, Next.js frontend.
See `SPEC.md` for the full design and `CLAUDE.md` for coding conventions.

## Run it (dev)

```bash
# 1. Database (postgres on host port 5434 + adminer on :8080)
docker compose up -d db

# 2. Backend  (http://localhost:8000, docs at /docs)
cd backend
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run python -m app.seed.seed_exercises
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend (http://localhost:3000)
cd frontend
pnpm install
pnpm dev
```

The frontend proxies `/api/*` to the backend, so open `http://localhost:3000`.

## Tests & lint

```bash
cd backend  && uv run ruff check . && uv run pytest
cd frontend && pnpm exec eslint . && pnpm build
```

## Layout
- `backend/` — FastAPI app, SQLAlchemy models, Alembic migrations, services, seed.
- `frontend/` — Next.js App Router UI with a generated, typed API client.
- `docker-compose.yml` — dev database; prod compose comes in Phase 7.
