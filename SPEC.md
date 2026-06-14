# SPEC.md — Personal PT Web App ("HomeShred")

> A self-hosted, rule-based personal trainer web app for home calisthenics + dumbbell training.
> This document is the source of truth for Claude Code. Build **incrementally, phase by phase**.
> Do **not** skip ahead. Each phase must compile, run, and pass its tests before the next begins.
> When a rule here is ambiguous, prefer the simplest correct implementation and leave a `# TODO(spec)` comment.

---

## 1. Goal & Scope

A **single-user (solo)** web app acting as a personal trainer:
- Generates **rule-based** workout plans (no ML/LLM yet).
- Guides the user through each workout (sets, reps, rest, timer).
- Tracks progress (volume, body metrics) and nutrition (calorie/macro targets).
- Applies **progressive overload** and **deload** automatically based on logged performance.

**Primary objective:** muscle gain + fat loss ("shred") → hypertrophy work + conditioning (HIIT/metcon) in a calorie deficit.

**Available equipment (hard constraint for exercise selection):**
- Pull-up bar (`pull_up_bar`)
- Dumbbells (`dumbbell`, assume adjustable pair)
- Bodyweight + floor (`bodyweight`)

> The generator MUST only select exercises whose `equipment ∈ {bodyweight, dumbbell, pull_up_bar}`. No barbell, machine, cable, kettlebell, band. A flat floor/mat is fine.

**Out of scope (now):** multi-user, auth, social, video hosting, payments, mobile-native.

---

## 2. Tech Stack

| Layer        | Choice                                                                 |
|--------------|------------------------------------------------------------------------|
| Frontend     | Next.js 16 (App Router, Turbopack default) + TypeScript (strict) + Tailwind + shadcn/ui   |
| Charts       | `recharts`                                                             |
| Backend      | FastAPI + Pydantic v2 + `pydantic-settings`                            |
| ORM          | SQLAlchemy 2.0 (async, `Mapped[]` style) + Alembic                     |
| DB           | PostgreSQL 17+ (Docker)                                                 |
| BE pkg mgr   | `uv` (`pyproject.toml` + `uv.lock`, local `.venv`)                     |
| FE pkg mgr   | `pnpm` (pinned via `packageManager`; Node 20+ — prod image uses node:22-slim, see §15) |
| FE API client| `openapi-typescript` + `openapi-fetch` generated from FastAPI OpenAPI  |
| Lint/format  | BE: `ruff` (lint+format). FE: `eslint` + `prettier`                    |
| Testing      | BE: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. FE: `vitest` (+ `@testing-library/react`) |
| Migrations   | Alembic, autogenerate + manual review                                  |

### Exercise data source
**Use `free-exercise-db`** (https://github.com/yuhonas/free-exercise-db — MIT, JSON with name/equipment/primaryMuscles/level/instructions). Ingest into our own `exercises` table via a seed script so we own the schema. Filter on import: keep only allowed equipment.

`wger` is a fallback if the dataset proves insufficient.

---

## 3. Repository Layout

```
homeshred/
├── docker-compose.yml          # postgres + adminer (optional)
├── README.md
├── CLAUDE.md                   # coding conventions (see separate file)
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py             # create_app() factory, router include, CORS
│   │   ├── config.py           # Settings(BaseSettings)
│   │   ├── db.py               # async engine, async_session, get_db dep
│   │   ├── enums.py            # all StrEnum definitions
│   │   ├── models/             # ORM: exercise.py, plan.py, session.py, metrics.py, profile.py
│   │   ├── schemas/            # Pydantic v2 request/response models
│   │   ├── api/                # routers: exercises, plans, sessions, progress, nutrition, profile, health
│   │   ├── services/
│   │   │   ├── plan_generator.py
│   │   │   ├── progression.py
│   │   │   ├── nutrition.py
│   │   │   └── volume.py
│   │   ├── data/
│   │   │   └── exercise_pools.py  # curated exercise → category/pattern mapping
│   │   └── seed/
│   │       ├── seed_exercises.py
│   │       └── free-exercise-db.json
│   └── tests/
│       ├── conftest.py
│       ├── test_plan_generator.py
│       ├── test_progression.py
│       └── test_nutrition.py
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── app/
    ├── components/
    ├── lib/
    │   ├── api.ts              # openapi-fetch client
    │   └── utils.ts
    └── ...
```

---

## 4. Enums (`app/enums.py`)

Use `enum.StrEnum`. Mirror these on the FE as TS union types.

```python
class Equipment(StrEnum):
    BODYWEIGHT = "bodyweight"
    DUMBBELL = "dumbbell"
    PULL_UP_BAR = "pull_up_bar"

class MovementPattern(StrEnum):       # used by the generator for balanced selection
    HORIZONTAL_PUSH = "horizontal_push"   # e.g. push-up, DB floor press
    VERTICAL_PUSH   = "vertical_push"     # e.g. DB shoulder press, pike push-up
    HORIZONTAL_PULL = "horizontal_pull"   # e.g. DB row, inverted row
    VERTICAL_PULL   = "vertical_pull"     # e.g. pull-up, chin-up
    SQUAT           = "squat"             # e.g. goblet squat, split squat
    HINGE           = "hinge"             # e.g. DB RDL, single-leg RDL
    CORE            = "core"              # e.g. plank, hanging leg raise
    CONDITIONING    = "conditioning"      # burpee, DB complex, mountain climber

class Focus(StrEnum):
    FULL_BODY    = "full_body"
    UPPER        = "upper"
    LOWER        = "lower"
    PUSH         = "push"
    PULL         = "pull"
    LEGS         = "legs"
    CONDITIONING = "conditioning"

class Level(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class Goal(StrEnum):
    SHRED = "shred"   # only goal for MVP; enum leaves room to grow

class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"

class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"          # ×1.2
    LIGHT = "light"                  # ×1.375
    MODERATE = "moderate"            # ×1.55
    ACTIVE = "active"                # ×1.725
    VERY_ACTIVE = "very_active"      # ×1.9
```

---

## 5. Data Model (PostgreSQL)

All PKs `int` identity unless noted. All timestamps `timestamptz`, stored UTC. Add indexes where noted.

### exercises  *(seeded, read-mostly)*
| col | type | notes |
|---|---|---|
| id | int pk | |
| name | text | not null |
| slug | text | unique, not null, index |
| equipment | text | enum `Equipment`, not null, index |
| pattern | text | enum `MovementPattern`, nullable (filled by curation step) |
| category | text | `push\|pull\|legs\|core\|conditioning`, index |
| primary_muscles | text[] | not null |
| secondary_muscles | text[] | default `{}` |
| level | text | enum `Level` |
| is_compound | bool | not null, default false |
| instructions | text[] | default `{}` |

### user_profile  *(single row, id always = 1)*
| col | type | notes |
|---|---|---|
| id | int pk | check `id = 1` |
| sex | text | enum `Sex` |
| age | int | check 14–100 |
| height_cm | numeric(5,1) | |
| weight_kg | numeric(5,1) | |
| activity_level | text | enum `ActivityLevel` |
| experience_level | text | enum `Level` |
| updated_at | timestamptz | |

### plans
| col | type | notes |
|---|---|---|
| id | int pk | |
| name | text | e.g. "Shred — 4 day Upper/Lower" |
| goal | text | enum `Goal` |
| days_per_week | int | check 3–5 |
| experience_level | text | enum `Level` |
| is_active | bool | default false; only one active at a time (enforce in service) |
| created_at | timestamptz | |

### plan_days
| col | type | notes |
|---|---|---|
| id | int pk | |
| plan_id | int fk → plans, on delete cascade | index |
| day_index | int | 1-based order within plan |
| focus | text | enum `Focus` |
| unique(plan_id, day_index) | | |

### plan_exercises
| col | type | notes |
|---|---|---|
| id | int pk | |
| plan_day_id | int fk → plan_days, cascade | index |
| exercise_id | int fk → exercises | |
| order_index | int | |
| sets | int | |
| target_reps_min | int | |
| target_reps_max | int | |
| rest_seconds | int | |
| is_conditioning | bool | default false |

### workout_sessions
| col | type | notes |
|---|---|---|
| id | int pk | |
| plan_day_id | int fk → plan_days, nullable | |
| date | date | not null, index |
| notes | text | nullable |
| completed | bool | default false |
| created_at | timestamptz | |

### set_logs
| col | type | notes |
|---|---|---|
| id | int pk | |
| session_id | int fk → workout_sessions, cascade | index |
| exercise_id | int fk → exercises | |
| set_number | int | 1-based |
| reps | int | |
| weight_kg | numeric(5,1) | nullable (null = pure bodyweight) |
| rpe | numeric(3,1) | nullable, 1–10 |

### body_metrics
| col | type | notes |
|---|---|---|
| id | int pk | |
| date | date | unique, index |
| weight_kg | numeric(5,1) | |
| body_fat_pct | numeric(4,1) | nullable |
| waist_cm | numeric(5,1) | nullable |

### nutrition_targets
| col | type | notes |
|---|---|---|
| id | int pk | |
| date | date | |
| tdee_kcal | int | |
| target_kcal | int | |
| protein_g | int | |
| carbs_g | int | |
| fat_g | int | |

---

## 6. CORE: Plan Generator (`services/plan_generator.py`)

This is the most important module. Keep all tunable values in **module-level config dicts** so rules are data-driven, not buried in code. Every rule below gets a comment referencing this section.

### 6.1 Input
```python
def generate_plan(goal: Goal, days_per_week: int, level: Level,
                  available_equipment: set[Equipment]) -> PlanDraft: ...
```

### 6.2 Split templates (by days/week)
A split is a list of (focus, pattern-slots). Pattern-slots define which `MovementPattern`s to fill.

```python
SPLITS: dict[int, list[Focus]] = {
    3: [Focus.FULL_BODY, Focus.FULL_BODY, Focus.FULL_BODY],
    4: [Focus.UPPER, Focus.LOWER, Focus.UPPER, Focus.LOWER],
    5: [Focus.PUSH, Focus.PULL, Focus.LEGS, Focus.UPPER, Focus.CONDITIONING],
}
```

### 6.3 Pattern slots per focus
Each focus pulls a fixed set of patterns. Compounds first, then accessories, then core, then optional conditioning.

```python
FOCUS_PATTERNS: dict[Focus, list[MovementPattern]] = {
    Focus.FULL_BODY: [SQUAT or HINGE (alternate per day), HORIZONTAL_PUSH or VERTICAL_PUSH,
                      VERTICAL_PULL or HORIZONTAL_PULL, CORE],
    Focus.UPPER:     [HORIZONTAL_PUSH, VERTICAL_PULL, VERTICAL_PUSH, HORIZONTAL_PULL, CORE],
    Focus.LOWER:     [SQUAT, HINGE, SQUAT (single-leg variant), CORE],
    Focus.PUSH:      [HORIZONTAL_PUSH, VERTICAL_PUSH, HORIZONTAL_PUSH (accessory), CORE],
    Focus.PULL:      [VERTICAL_PULL, HORIZONTAL_PULL, VERTICAL_PULL (accessory), CORE],
    Focus.LEGS:      [SQUAT, HINGE, SQUAT (single-leg), CORE],
    Focus.CONDITIONING: [CONDITIONING, CONDITIONING, CONDITIONING],
}
```
> Where it says "alternate per day", rotate the choice using `day_index % 2` so Full Body A/B/C differ.

**Implemented model (see `services/plan_generator.py`):** each entry above is a
`Slot(patterns: tuple[MovementPattern, ...], role)` where `role ∈ {compound,
accessory, core, conditioning}`. A slot with >1 pattern rotates by
`day_index % len(patterns)` (the "alternate per day" cases). The **role** is the
single source of truth for both (a) selection preference — compound slots prefer
`is_compound` exercises, accessory slots prefer non-compound — and (b) which
`PRESCRIPTION` row applies (§6.4). This is cleaner than re-deriving compound/accessory
from the chosen exercise, and keeps "the 3rd push is an accessory" intent explicit.

### 6.4 Shred prescription (sets / reps / rest)
Driven by whether the slot is a compound or accessory, plus level.

```python
PRESCRIPTION = {
    # (is_compound): (sets, reps_min, reps_max, rest_seconds)
    "compound":   {"sets": 4, "reps": (6, 10),  "rest": 75},
    "accessory":  {"sets": 3, "reps": (10, 15), "rest": 60},
    "core":       {"sets": 3, "reps": (12, 20), "rest": 45},
    "conditioning": {"sets": 3, "reps": (0, 0),  "rest": 45},  # reps=0 → time-based (see 6.7)
}
LEVEL_SET_MODIFIER = {Level.BEGINNER: -1, Level.INTERMEDIATE: 0, Level.ADVANCED: +1}  # applied to sets, floor 2
```
Rationale (shred = hypertrophy + metabolic stress in a deficit): moderate-high reps, short rests. Comment this in code.

### 6.5 Conditioning placement
- 3-day: add 1 conditioning block to **2** of the 3 days (the 2nd and 3rd).
- 4-day: add 1 conditioning block to **2** days (after the 2 Lower days).
- 5-day: day 5 IS a conditioning day (3 blocks); plus add 1 block to Push and Pull days. Total 2–3 conditioning exposures/week.

### 6.6 Exercise selection algorithm
For each pattern slot in a day:
1. Filter `exercises` where `pattern == slot` AND `equipment ∈ available_equipment` AND `level <= user level` (beginner can't get advanced; advanced can use all).
2. Prefer `is_compound == True` for the first slots of the day, accessories afterwards.
3. **No duplicate exercise within the same plan** unless the filtered pool is exhausted (then allow reuse but not within the same day).
4. Deterministic-but-varied: seed the RNG with `hash((plan_id_placeholder, day_index, slot_index))` so regeneration is reproducible in tests but plans look varied. Selection uses `random.Random(seed).choice(...)`.
5. Attach prescription from 6.4 based on compound/accessory/core/conditioning.

### 6.7 Conditioning exercises (time-based)
Conditioning `plan_exercises` use `is_conditioning=True`, `target_reps_min/max = 0`, and `rest_seconds` as work/rest. Represent work duration by convention: store `sets` = rounds, and the FE timer treats a conditioning block as `rounds × (40s work / 20s rest)` (EMOM-style). Document this convention in both BE and FE.

### 6.8 Output
Return a `PlanDraft` dataclass (plan + days + exercises) that the API layer persists in one transaction. Set `is_active=True` and deactivate any previously active plan.

### 6.9 Hard tests (must exist)
- `test_no_disallowed_equipment`: generate plans for days 3/4/5 × levels; assert every selected exercise's equipment ∈ available set. **Fail = build not done.**
- `test_split_day_count`: days created == days_per_week.
- `test_prescription_ranges`: compound reps within (6,10), accessory within (10,15), etc.
- `test_reproducible`: same input + same seed → identical plan.
- `test_no_intraday_duplicates`: no exercise repeats within a single day.

---

## 7. Progression & Deload (`services/progression.py`)

Applied when starting a new session OR generating a new mesocycle. Rule-based double-progression:

```python
# For each plan_exercise, look at the most recent completed session's set_logs:
# 1. If the user hit the TOP of the rep range on ALL sets last time:
#       - weighted exercise (weight_kg not null): increase weight by +2.5kg (DB) next time, reset reps to bottom of range.
#       - bodyweight exercise: increase target_reps_max by +2 (progress via reps), capped at +50% of original.
# 2. If the user hit the BOTTOM or below on 2+ consecutive sessions:
#       - reduce weight by 10% (deload) OR reduce sets by 1.
# 3. Deload week: every 4th week (mesocycle), multiply all sets' load by 0.6 and reduce sets by 1 (recovery).
```
Track week number via `plans.created_at` vs session dates (week = floor(days since plan start / 7) + 1).

Expose helper `suggest_next_targets(plan_exercise, recent_logs) -> dict` returning `{sets, reps_min, reps_max, suggested_weight_kg}`. The session runner shows these as defaults.

Tests: `test_progression_increases_on_top_range`, `test_deload_on_stall`, `test_mesocycle_deload_week`.

---

## 8. Nutrition (`services/nutrition.py`)

**BMR — Mifflin-St Jeor:**
```
male:   BMR = 10*kg + 6.25*cm - 5*age + 5
female: BMR = 10*kg + 6.25*cm - 5*age - 161
```
**TDEE** = BMR × activity factor (see `ActivityLevel` map in §4).

**Shred targets:**
```
target_kcal = round(TDEE * 0.80)               # 20% deficit
protein_g   = round(2.0 * weight_kg)           # 1.8–2.2 g/kg; use 2.0 to preserve muscle in deficit
fat_g       = round(0.8 * weight_kg)
remaining   = target_kcal - (protein_g*4 + fat_g*9)
carbs_g     = max(0, round(remaining / 4))
```
Persist a `nutrition_targets` row dated today. Recompute on profile change.

Tests: known-input vectors for male/female; assert kcal from macros ≈ target_kcal (±2%).

---

## 9. Volume aggregation (`services/volume.py`)

Weekly **training volume** = Σ (sets × reps × weight_kg) per primary muscle group, grouped by ISO week. For bodyweight (`weight_kg` null), use a bodyweight proxy: `reps × (profile.weight_kg × muscle_factor)` where `muscle_factor` defaults to 1.0 (document the simplification). Endpoint returns `[{week, muscle, volume}]`.

---

## 10. API (FastAPI, prefix `/api`, all async)

Each endpoint lists request → response Pydantic schema names.

```
GET   /api/health                         → {status:"ok"}

GET   /api/exercises                       ?equipment&muscle&category&pattern  → list[ExerciseOut]
GET   /api/exercises/{id}                  → ExerciseOut

GET   /api/profile                         → ProfileOut
PUT   /api/profile          ProfileIn      → ProfileOut       # upserts row id=1; also recomputes nutrition targets (§8)

POST  /api/plans            PlanCreateIn   → PlanOut          # {goal, days_per_week}; generates+persists, activates
GET   /api/plans                            → list[PlanSummaryOut]
GET   /api/plans/{id}                        → PlanDetailOut   # nested days→exercises
PATCH /api/plans/{id}/activate              → PlanSummaryOut

POST  /api/sessions         SessionCreateIn → SessionOut       # {plan_day_id, date?}; returns suggested targets per exercise
GET   /api/sessions/{id}                     → SessionOut       # session + logs (used by the FE workout runner)
POST  /api/sessions/{id}/sets  SetLogIn     → SetLogOut
PATCH /api/sessions/{id}/complete           → SessionOut
GET   /api/sessions          ?from&to        → list[SessionOut]

GET   /api/progress/volume   ?from&to        → list[VolumePoint]   # {week,muscle,volume}

POST  /api/body-metrics      BodyMetricIn    → BodyMetricOut
GET   /api/body-metrics      ?from&to        → list[BodyMetricOut]

GET   /api/nutrition/targets                 → NutritionTargetOut  # latest
POST  /api/nutrition/recompute               → NutritionTargetOut  # from current profile
```

Error handling: 404 for missing ids, 422 from Pydantic, 409 if generating a plan with no profile set. Return RFC-7807-ish `{detail}` bodies.

---

## 11. Frontend (Next.js App Router, mobile-first)

| Route | Purpose | Key UI |
|---|---|---|
| `/` | Dashboard | active plan card, today's workout CTA, bodyweight sparkline, today's macro targets |
| `/profile` | edit profile | form; on save → `POST /nutrition/recompute` |
| `/plan/new` | generate | select days/week (3/4/5) → `POST /plans` → redirect to `/plan` |
| `/plan` | view active plan | accordion of days → exercises with sets×reps @ rest |
| `/workout/[planDayId]` | **session runner** | per-exercise set rows (reps/weight inputs prefilled from `suggest_next_targets`), checkmark per set, **rest countdown timer** with audio beep, "complete workout" button |
| `/progress` | charts | recharts: weekly volume per muscle (stacked bar), bodyweight line |
| `/nutrition` | targets | TDEE + macro rings/cards |

Session runner details:
- Rest timer: countdown using `rest_seconds`; auto-start when a set is checked; audio cue (`<audio>` beep) + vibration (`navigator.vibrate`) on finish.
- Conditioning block: render as rounds × (40s work / 20s rest) interval timer (see §6.7).
- Persist set logs immediately via `POST /sessions/{id}/sets` (optimistic UI).
- Big tap targets; sticky timer bar at bottom on mobile.

FE state: server state via the generated openapi-fetch client + React Query (TanStack). No global store needed beyond that.

---

## 12. Build Phases (strict order)

**Phase 0 — Scaffolding**
- `docker-compose.yml` (postgres:17 + adminer). `uv init` backend, `pnpm create next-app` frontend.
- `GET /api/health`. CORS for `localhost:3000`. Confirm both servers run + FE can hit health.

**Phase 1 — Data layer**
- All ORM models + enums. Alembic initial migration. `seed_exercises.py` ingests `free-exercise-db.json`, normalizes equipment, **curates `pattern` + `is_compound`** using `data/exercise_pools.py` mapping. Verify row counts per pattern (assert each non-conditioning pattern has ≥3 allowed exercises, else log a warning).

**Phase 2 — Exercises + Profile API/FE**
- exercises + profile endpoints + schemas. FE `/profile` page and an exercises browser.

**Phase 3 — Plan generator (CORE)**
- `plan_generator.py` + `exercise_pools.py` + `POST/GET /plans`. All §6.9 tests pass. FE `/plan/new` + `/plan`.

**Phase 4 — Session runner + progression**
- sessions/set-logs endpoints + `progression.py` (`suggest_next_targets`). FE `/workout/[planDayId]` with timers. §7 tests pass.

**Phase 5 — Progress + body metrics**
- `volume.py` + endpoints + body-metrics. FE `/progress` charts.

**Phase 6 — Nutrition**
- `nutrition.py` + endpoints. FE `/nutrition`. §8 tests pass.

After each phase: update `README.md` run instructions, run `ruff` (no errors), commit.

---

## 13. Definition of Done (MVP)

User can: set profile → generate a shred plan (3/4/5 days) → open today's workout → log sets with prefilled progression targets and a working rest timer → complete the session → see weekly volume + bodyweight trends → see daily calorie/macro targets.

Two run modes both work:
- **Dev:** `docker compose up` (db) + `uv run` backend + `pnpm dev` frontend.
- **Self-host (target):** `docker compose -f docker-compose.prod.yml up -d --build` on the Ubuntu homelab host — all three containers healthy, migrations applied, exercises seeded, app reachable at `http://<host>:3000` over LAN and Tailscale, no public exposure, no reverse proxy.

All listed tests pass; no lint errors.

---

## 14. Deployment / Self-hosting (Docker, LAN-only)

Target: a single Ubuntu host (homelab). All services run as Docker containers via one compose file. **No reverse proxy, not public** — accessed over LAN / Tailscale only. The frontend proxies API calls to the backend internally, so the browser only ever talks to the frontend's origin (no CORS config, no hardcoded backend IP).

### 14.1 Files to add
```
homeshred/
├── docker-compose.yml          # DEV: postgres + adminer only (keep as is)
├── docker-compose.prod.yml     # PROD: db + backend + frontend (new)
├── .env.prod.example           # prod env template (new)
├── backend/Dockerfile          # new
└── frontend/Dockerfile         # new
```

### 14.2 Backend Dockerfile (multi-stage, uv)
- Stage 1 (builder): `python:3.12-slim`, install `uv`, copy `pyproject.toml` + `uv.lock`, `uv sync --frozen --no-dev` into `/app/.venv`.
- Stage 2 (runtime): `python:3.12-slim`, copy `/app/.venv` + app code, non-root user, `EXPOSE 8000`.
- Entrypoint runs migrations then starts the server:
  `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`
  (Use the multi-worker option later if needed; single worker is fine for solo use.)

### 14.3 Frontend Dockerfile (Next.js 16 standalone)
- In `next.config.js` set `output: "standalone"` so the runtime image is small.
- Multi-stage: `node:20-slim` deps → build (`pnpm build`) → runtime copies `.next/standalone` + `.next/static` + `public`. `EXPOSE 3000`. Run `node server.js`.

### 14.4 API proxying (the key bit — no reverse proxy)
In `frontend/next.config.js`, rewrite `/api/*` to the backend **service name** on the internal Docker network:
```js
async rewrites() {
  return [{ source: "/api/:path*", destination: `${process.env.BACKEND_INTERNAL_URL}/api/:path*` }];
}
// BACKEND_INTERNAL_URL = "http://backend:8000" inside the compose network
```
- The FE `openapi-fetch` client uses **relative** baseUrl `/api` → the browser hits the frontend origin, Next.js forwards it to `backend:8000` server-side. No CORS needed; you can drop the CORS middleware (or keep it permissive for LAN).
- Result: you only expose **one** port to the host (frontend `3000`). Backend stays internal to the compose network.

### 14.5 docker-compose.prod.yml (shape)
```yaml
services:
  db:
    image: postgres:17
    environment: [POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]   # from .env.prod
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck: pg_isready -U $POSTGRES_USER         # interval 10s
    restart: unless-stopped
  backend:
    build: ./backend
    env_file: .env.prod
    depends_on: { db: { condition: service_healthy } }
    healthcheck: curl -f http://localhost:8000/api/health
    restart: unless-stopped
    # no host port published — only reachable inside the network as "backend"
  frontend:
    build:
      context: ./frontend
      args: [BACKEND_INTERNAL_URL=http://backend:8000]
    environment: [BACKEND_INTERNAL_URL=http://backend:8000]
    depends_on: { backend: { condition: service_healthy } }
    ports: ["3000:3000"]            # the ONLY exposed port
    restart: unless-stopped
volumes:
  pgdata:
```

### 14.6 Access
- On the host or LAN: `http://<ubuntu-host-ip>:3000`
- Remote: via Tailscale → `http://<tailscale-hostname>:3000` (no extra config; Tailscale handles it). If you want a clean hostname later, Tailscale Serve can map it without exposing publicly.

### 14.7 Operations
- Seed exercises on first deploy: `docker compose -f docker-compose.prod.yml run --rm backend python -m app.seed.seed_exercises` (idempotent — upsert by `slug`, safe to re-run).
- Backups: `pg_dump` the `pgdata` volume on a cron (homelab nicety; optional for MVP).
- Bring up: `docker compose -f docker-compose.prod.yml up -d --build`.

### 14.8 Phase 7 — Containerize & deploy (add to build order)
Add as the final phase after §12 Phase 6:
- Write both Dockerfiles + `docker-compose.prod.yml` + `.env.prod.example` + `next.config.js` rewrite + `output: "standalone"`.
- Verify a clean `up -d --build` on the Ubuntu host brings all three healthy, migrations apply, seed runs, and the app is reachable at `:3000` over LAN and Tailscale.
- This phase is part of Definition of Done for self-hosting.

---

## 15. Implementation Notes & Deviations

Decisions made during the build that refine or deviate from the text above. Kept
here so the spec stays the source of truth.

- **Dev DB host port.** `docker-compose.yml` publishes Postgres on host **5434**
  (not 5432) because 5432/5433 were taken by other containers on the dev host.
  `.env.example` / READMEs match. The container port is still 5432; prod is unaffected.
- **Frontend prod image = `node:22-slim`** (spec §14.3 said node:20). Corepack's
  bundled pnpm threw `ERR_UNKNOWN_BUILTIN_MODULE` on node:20; node 22 satisfies
  §2's "Node 20+". pnpm is pinned (`packageManager: pnpm@11.5.2` + `corepack prepare`).
- **Prod `db` service uses `env_file: .env.prod`** rather than an `environment:`
  block — Compose interpolates `${VAR}` from `.env`, not `.env.prod`, so the block
  would have been empty. The healthcheck resolves `${POSTGRES_USER}` at runtime.
- **Enum storage.** `db.enum_col()` persists StrEnum **values** (e.g. `"dumbbell"`)
  as VARCHAR + CHECK via `values_callable` (CLAUDE.md "store as text").
- **Plan generator is pure.** `generate_plan(..., exercises)` takes the candidate
  list as a parameter (not a DB handle), so §6.9 tests run with no DB. The API
  layer loads exercises and persists the returned `PlanDraft`.
- **Conditioning data.** free-exercise-db has no "burpee"; conditioning is covered
  by plyometric jumps, mountain climbers, wind sprints and a dumbbell swing.
- **Profile PUT recomputes nutrition** (so the dashboard is always current), and a
  convenience `GET /api/sessions/{id}` was added for the workout runner.
- **Test isolation.** Backend tests use a function-scoped async engine (NullPool) with
  a fresh schema per test — chosen over savepoint-rollback because asyncpg connections
  are bound to the event loop and a session-scoped engine crossed loops.
- **FE tests (vitest).** Pure helpers extracted for testability: `lib/timer.ts`
  (`intervalState`/`isBoundary`) and `lib/charts.ts` (`pivotVolume`), plus a
  fake-timer test of `RestTimer` and UI smoke tests.

---

## 16. Rule Engine — Limitations & Roadmap

The current generator/progression is intentionally simple (SPEC §1: "rule-based, no
ML/LLM yet"). Known limitations and a prioritized path to improve it **without**
adding ML:

**Current limitations**
1. **Volume is not periodised across the mesocycle** — only the week-4 deload varies
   load; weeks 1–3 are flat. Real hypertrophy programs ramp volume then deload.
2. **Progression is per-exercise and memoryless beyond the last 1–3 sessions** — it
   can't see a multi-week trend (e.g. slow grind vs. true stall).
3. **No fatigue / recovery model** — RPE is logged but unused; back-to-back hard days
   aren't balanced.
4. **Selection variety is seeded but static** — the same seed yields the same plan;
   there's no anti-staleness rotation across regenerations or weeks.
5. **Bodyweight volume proxy is crude** (`reps × bodyweight × 1.0`) — per-exercise
   load fractions would make the volume chart meaningful.
6. **No per-muscle weekly volume targets** — the plan doesn't check it lands each
   muscle in an effective set range (e.g. 10–20 hard sets/week).

**Roadmap (rule-based, ordered by value/effort)**
- **R1 — Set-volume targeting. ✅ DONE.** `WEEKLY_SET_TARGETS[muscle]` defines weekly
  minimums; `generate_plan` runs a deterministic post-pass (`_apply_volume_targeting`)
  that adds sets to existing exercises (capped at `MAX_SETS_PER_EXERCISE`) until each
  targeted muscle meets its minimum. Volume credits primary movers fully and secondary
  movers at ½ (so arms/glutes accrue from compounds). `coverage_report` +
  `GET /api/plans/{id}/coverage` surface it; the FE shows a coverage card. Tested in
  `test_plan_generator.py` (targets met-or-capped, cap respected, report shape).
- **R2 — Linear periodisation.** Add a week→(sets, intensity) curve so weeks 1–3 ramp
  and week 4 deloads, derived from `week_number` (already computed in §7).
- **R3 — RPE-aware progression. ✅ DONE.** `suggest_next_targets` now uses logged RPE:
  progress only when last session was at top range AND avg RPE ≤ `RPE_PROGRESS_CEILING`
  (8.0); hold if reps were hit but RPE was higher; deload on a rep stall OR a sustained
  grind (2 sessions ≥ `RPE_DELOAD_FLOOR` = 9.5). No-RPE logs fall back to the rep-only
  rule (backward compatible). The FE workout runner captures per-set RPE. Tested in
  `test_progression.py`.
- **R4 — Per-exercise bodyweight load factors** in `exercise_pools.py` to fix the
  volume proxy (R5 depends on this).
- **R5 — Anti-staleness rotation.** Seed selection with the mesocycle week so
  exercises rotate over time while staying reproducible per (plan, week).
- **R6 — Fatigue balancing.** Spread high-CNS movements (e.g. heavy hinge/pull) across
  the split and avoid stacking them on consecutive days.
- **R7 — Age-based recovery/volume. ✅ DONE.** The profile `age` now feeds the workout
  plan (previously only nutrition): `AGE_ADJUSTMENTS` bands (≥55, ≥40, else) yield a
  `rest_multiplier` (longer rests with age — ×1.10 / ×1.20) and a `volume_factor` that
  scales `WEEKLY_SET_TARGETS` down (×0.90 / ×0.80, floored). `generate_plan(..., age)`
  applies both; `create_plan` passes `profile.age`; the coverage report/endpoint scale
  with age too. Tested in `test_plan_generator.py`. So the plan is now customized by
  **age + experience + days + equipment + adaptive progression**, and nutrition by the
  full body-measure set (sex/age/height/weight/activity).

All of the above stay deterministic and unit-testable, preserving the "no ML"
constraint while making the output meaningfully smarter.
