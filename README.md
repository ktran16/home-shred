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
- **Meal templates** (`/nutrition`): save a day's foods under a name, then log them all into
  any day in one tap (×0.5 / ×1 / ×2 portions). Each food lands as its own log entry.
- **Voice coach** (`/workout`): server-side neural TTS (Piper) reads cues in English or
  Vietnamese. The workout runner pre-generates a session's cue audio at start, so playback
  is instant. Download the voice models once with `make tts-voices` (dev) /
  `make prod-tts-voices` (prod); without them it falls back to browser speech.
  - *Optional, higher-quality Vietnamese*: F5-TTS (a neural voice-cloning model) sounds far
    less robotic than Piper's VI voice. Install the extras on the host that generates cues
    (`cd backend && uv pip install -e '.[f5]'`), download the model (`make tts-f5`), and set
    `TTS_VI_ENGINE=f5`. It's heavy (torch) and kept out of the runtime image; if the extras
    or model are missing it silently falls back to Piper. The cloned voice defaults to a
    bundled Southern-Vietnamese female clip from the VIVOS corpus (CC BY-NC-SA 4.0 — personal/
    non-commercial use; see `backend/assets/ATTRIBUTION.md`). Swap `media/tts/f5/ref.wav` (and
    `TTS_F5_REF_TEXT`) to change the voice.

What's next is brainstormed in `SPEC.md §19` (ops hardening → PWA/offline → plan lifecycle).

## Run it (dev)

```bash
# 1. Database (postgres on host port 5434 + adminer on :8080)
docker compose up -d db
docker exec homeshred-dev-db-1 createdb -U homeshred homeshred_test   # first run only (tests)

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

# 4. (optional) Voice-coach TTS models for English + Vietnamese
make tts-voices
```

The frontend proxies `/api/*` to the backend, so open `http://localhost:3000`.

Dev compose runs as project `homeshred-dev` (volume `homeshred-dev_pgdata`); prod runs as
`selfhostedpt` (volumes `selfhostedpt_pgdata` / `selfhostedpt_media`). They never share a
volume, so `docker compose down -v` in dev cannot touch prod data.

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

# first deploy only — download the voice-coach TTS models into the media volume:
make prod-tts-voices
```

The backend container applies Alembic migrations on start. Open
`http://<host-ip>:3000` on the LAN, or `http://<tailscale-host>:3000` remotely.

### Backups

`make prod-backup` writes a dated set into `./backups/daily/` (gitignored): a
`pg_dump -Fc` of the DB plus a tarball of the media volume (progress photos; TTS
voices/cache are skipped — re-fetch with `make prod-tts-voices`). The first backup in
any 7-day window is also hard-linked into `backups/weekly/`; rotation keeps 7 daily +
4 weekly sets (`BACKUP_DIR`, `KEEP_DAILY`, `KEEP_WEEKLY` override). Daily via host cron:

```cron
15 3 * * * cd /path/to/selfhostedPT && make prod-backup >> backups/backup.log 2>&1
```

Check a backup with `make prod-restore-test FILE=backups/daily/homeshred-<stamp>.dump`:
it restores into a throwaway `postgres:17` container and prints per-table row counts,
never touching prod. `make prod-restore FILE=... CONFIRM=yes` runs that test, then
**replaces** the prod DB and unpacks the matching media tarball.

## Make targets

A root `Makefile` wraps both compose files; run `make help` for the full list.

```bash
make up            # dev: start postgres + adminer
make prod-up       # prod: build + start db + backend + frontend
make prod-seed     # prod: seed the exercise catalogue
make prod-health   # prod: curl the frontend + /api/health
make prod-backup   # prod: dump db + media into ./backups (rotated)
make prod-restore-test FILE=backups/daily/<set>.dump  # prod: verify a backup in a scratch db
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
