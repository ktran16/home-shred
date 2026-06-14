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

## Self-host (prod, LAN/Tailscale only)

One compose file runs db + backend + frontend; only the frontend port (3000) is
published — the backend stays internal and the browser only talks to the FE origin
(no reverse proxy, no CORS). See SPEC §14.

```bash
cp .env.prod.example .env.prod          # set strong POSTGRES_PASSWORD + matching DATABASE_URL
docker compose -f docker-compose.prod.yml up -d --build

# first deploy only — seed the exercise catalogue (idempotent):
docker compose -f docker-compose.prod.yml run --rm backend python -m app.seed.seed_exercises
```

The backend container applies Alembic migrations on start. Open
`http://<host-ip>:3000` on the LAN, or `http://<tailscale-host>:3000` remotely.

## Layout
- `backend/` — FastAPI app, SQLAlchemy models, Alembic migrations, services, seed; `Dockerfile`.
- `frontend/` — Next.js App Router UI with a generated, typed API client; `Dockerfile` (standalone).
- `docker-compose.yml` — dev database (postgres + adminer).
- `docker-compose.prod.yml` + `.env.prod.example` — self-host stack.
