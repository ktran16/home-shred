# HomeShred

A self-hosted, rule-based personal-trainer web app for home calisthenics + dumbbell
training (muscle gain + fat loss). FastAPI + PostgreSQL backend, Next.js frontend.
See `SPEC.md` for the full design and `CLAUDE.md` for coding conventions.

## Local-first smart features (SPEC §17)
All run on-device or in-process — no cloud, CPU-only friendly:
- **Camera rep counting + form check** (`/workout`): MediaPipe Pose in the browser
  auto-counts reps and flags partial range of motion. Video never leaves the phone.
- **Next-session forecast** (`/progress`): per-exercise trend-based load / readiness.
- **Adaptive TDEE** (`/nutrition`): real maintenance calories from your bodyweight trend.
- **Exercise search** (`/exercises`): "a hamstring exercise like an RDL".
- **Barcode food lookup** (`/nutrition`): scan a barcode → macros (via Open Food Facts).
- **Food log** (`/nutrition`): manual/barcode entries with daily totals and remaining macros.

What's next is brainstormed in `SPEC.md §19` (ops hardening → PWA/offline → plan lifecycle).

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

## Make targets

A root `Makefile` wraps both compose files; run `make help` for the full list.

```bash
make up            # dev: start postgres + adminer
make prod-up       # prod: build + start db + backend + frontend
make prod-seed     # prod: seed the exercise catalogue
make prod-health   # prod: curl the frontend + /api/health
make prod-reset    # prod: DESTRUCTIVE — drop db volume, rebuild, re-seed
```

`prod-reset` is the routine required after any DB password change (Postgres only
applies `POSTGRES_PASSWORD` on the first init of an empty data dir).

## Layout
- `backend/` — FastAPI app, SQLAlchemy models, Alembic migrations, services, seed; `Dockerfile`.
- `frontend/` — Next.js App Router UI with a generated, typed API client; `Dockerfile` (standalone).
- `docker-compose.yml` — dev database (postgres + adminer).
- `docker-compose.prod.yml` + `.env.prod.example` — self-host stack.
- `Makefile` — dev/prod compose shortcuts (`make help`).
