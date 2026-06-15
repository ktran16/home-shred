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

class ExercisePreferenceStatus(StrEnum):
    FAVORITE = "favorite"
    AVOID = "avoid"

class FoodLogSource(StrEnum):
    MANUAL = "manual"
    BARCODE = "barcode"
    LLM = "llm"
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
| bodyweight_load_factor | float | not null, default 1.0; volume proxy for bodyweight exercises (§16 R4) |
| instructions | text[] | default `{}` |

### exercise_preferences
| col | type | notes |
|---|---|---|
| exercise_id | int pk/fk → exercises, on delete cascade | |
| status | text | enum `ExercisePreferenceStatus`, index |
| updated_at | timestamptz | |

### user_profile
Profiles are still single-user app settings, not auth users. Exactly one profile should
be active at a time; other profiles are saved presets.

| col | type | notes |
|---|---|---|
| id | int pk | identity |
| name | text | not null, non-empty |
| is_active | bool | default false, index; service enforces one active |
| sex | text | enum `Sex` |
| age | int | check 14–100 |
| height_cm | numeric(5,1) | |
| weight_kg | numeric(5,1) | |
| activity_level | text | enum `ActivityLevel` |
| experience_level | text | enum `Level` |
| limitations | text[] | default `{}`; allowed: shoulder, knee, lower_back, wrist, pull_up |
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

### food_log
| col | type | notes |
|---|---|---|
| id | int pk | |
| date | date | not null, index |
| name | text | not null, non-empty |
| grams | numeric(7,1) | check > 0 |
| kcal | int | check >= 0 |
| protein_g | numeric(7,1) | check >= 0 |
| carbs_g | numeric(7,1) | check >= 0 |
| fat_g | numeric(7,1) | check >= 0 |
| source | text | enum `FoodLogSource`, index |
| barcode | text | nullable |
| created_at | timestamptz | |

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

Weekly **training volume** = Σ (sets × reps × weight_kg) per primary muscle group,
grouped by ISO week. For bodyweight (`weight_kg` null), use the §16 R4 proxy:
`reps × (profile.weight_kg × exercise.bodyweight_load_factor)`, defaulting the factor
to 1.0 for uncurated exercises. Endpoint returns `[{week, muscle, volume}]`.

---

## 10. API (FastAPI, prefix `/api`, all async)

Each endpoint lists request → response Pydantic schema names.

```
GET   /api/health                         → {status:"ok"}

GET   /api/exercises                       ?equipment&muscle&category&pattern  → list[ExerciseOut]
GET   /api/exercises/search                ?q&limit  → list[ExerciseSearchHitOut]  # local semantic-ish search (§17.3 A3)
GET   /api/exercises/{id}                  → ExerciseOut
GET   /api/exercises/{id}/history          ?sessions  → ExerciseHistoryOut   # recent completed sessions for this exercise (§16 follow-up)
PUT   /api/exercises/{id}/preference  ExercisePreferenceIn → ExercisePreferenceOut  # favorite/avoid
DELETE /api/exercises/{id}/preference       → 204

GET   /api/profile                         → ProfileOut
PUT   /api/profile          ProfileIn      → ProfileOut       # upserts active profile; recomputes nutrition targets (§8)
POST  /api/profile          ProfileIn      → ProfileOut       # creates and activates a named profile
GET   /api/profile/all                     → list[ProfileOut] # active first
PATCH /api/profile/{profile_id}/activate   → ProfileOut       # activates profile; recomputes nutrition targets
DELETE /api/profile/{profile_id}           → 204              # 409 if deleting the last profile

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
GET   /api/progress/strength                 → list[ExerciseStrengthOut]  # per-exercise PRs + e1RM trend (§18)
GET   /api/progress/prediction               → list[LoadPredictionOut]    # next-session load/readiness forecast (§17.3 A2)

POST  /api/body-metrics      BodyMetricIn    → BodyMetricOut
GET   /api/body-metrics      ?from&to        → list[BodyMetricOut]

GET   /api/nutrition/targets                 → NutritionTargetOut  # latest
POST  /api/nutrition/recompute               → NutritionTargetOut  # from current profile
GET   /api/nutrition/log        ?date         → DailyFoodLogOut     # daily entries/totals/remaining (§19.1)
POST  /api/nutrition/log        FoodLogIn     → DailyFoodLogOut     # manual/barcode/llm-source entry (§19.1)
GET   /api/nutrition/log/recent ?limit        → list[FoodLogRecentOut]  # recent distinct foods for quick-add (§19.5)
POST  /api/nutrition/log/copy-day FoodLogCopyDayIn → DailyFoodLogOut # clone a day's entries; 404 if source empty (§19.5)
GET   /api/nutrition/log/history ?end_date&days → NutritionHistoryOut # 7-day adherence/trend (§19.5)
DELETE /api/nutrition/log/{id}                → DailyFoodLogOut     # delete entry, return updated day (§19.1)
GET   /api/nutrition/adaptive                → AdaptiveTDEEOut     # adaptive-TDEE preview (§17.3 A1)
POST  /api/nutrition/adaptive/apply          → NutritionTargetOut  # persist today's adaptive target (§17.3 A1)
GET   /api/nutrition/barcode/{code}          → FoodFactsOut        # Open Food Facts macro lookup (§17.5 B2b, external)
```

Error handling: 404 for missing ids, 422 from Pydantic, 409 if generating a plan with no profile set. Return RFC-7807-ish `{detail}` bodies.

---

## 11. Frontend (Next.js App Router, mobile-first)

| Route | Purpose | Key UI |
|---|---|---|
| `/` | Dashboard | active plan card, today's workout CTA, bodyweight sparkline, today's macro targets |
| `/profile` | manage profile | named profile switcher + form; save/switch/create recomputes targets |
| `/plan/new` | generate | select days/week (3/4/5) → `POST /plans` → redirect to `/plan` |
| `/plan` | view active plan | accordion of days → exercises with sets×reps @ rest |
| `/workout/[planDayId]` | **session runner** | per-exercise set rows (reps/weight inputs prefilled from `suggest_next_targets`), checkmark per set, **rest countdown timer** with audio beep, "complete workout" button |
| `/progress` | charts | recharts: weekly volume per muscle (stacked bar), bodyweight line |
| `/nutrition` | targets + food log | TDEE + macro cards, adaptive TDEE, barcode lookup, daily food log |

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
- exercises + profile endpoints + schemas. FE `/profile` manager and an exercises browser.

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
- **Named active profiles.** The original singleton `user_profile` became a small
  profile manager: `GET /api/profile` remains backward-compatible and returns the
  active profile, while `POST /api/profile`, `GET /api/profile/all`,
  `PATCH /api/profile/{profile_id}/activate`, and `DELETE /api/profile/{profile_id}`
  manage saved profile presets. Training/nutrition data is still global to the solo
  app; see §19.4 if profile-scoped data is ever needed.
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
- **R2 — Mesocycle periodisation. ✅ DONE.** `WEEK_PERIODISATION` maps the 4-week block
  position → volume multiplier (1.0 / 1.1 / 1.2 / 0.6) applied to base sets and the
  weekly targets, so weeks 1–3 accumulate and week 4 deloads. `generate_plan(..., week)`;
  plans persist `mesocycle_week`; the FE "Next week" button advances the block.
- **R3 — RPE-aware progression. ✅ DONE.** `suggest_next_targets` now uses logged RPE:
  progress only when last session was at top range AND avg RPE ≤ `RPE_PROGRESS_CEILING`
  (8.0); hold if reps were hit but RPE was higher; deload on a rep stall OR a sustained
  grind (2 sessions ≥ `RPE_DELOAD_FLOOR` = 9.5). No-RPE logs fall back to the rep-only
  rule (backward compatible). The FE workout runner captures per-set RPE. Tested in
  `test_progression.py`.
- **R4 — Per-exercise bodyweight load factors. ✅ DONE.** `BODYWEIGHT_LOAD_FACTORS` in
  `exercise_pools.py` (push-up ≈ 0.64, pull-up ≈ 1.0, plank ≈ 0.3, …) is seeded onto
  `exercises.bodyweight_load_factor` (new migration). `volume.py` now uses
  `reps × bodyweight × load_factor` for bodyweight sets instead of full bodyweight.
- **R5 — Anti-staleness rotation. ✅ DONE.** The selection RNG seed includes the
  mesocycle week (`hash((placeholder, week, day, slot))`), so exercises rotate week to
  week while staying reproducible per (week, day, slot). Combines with R2: each new week
  is both periodised and freshly rotated.
- **R6 — Fatigue management. ✅ DONE.** `PATTERN_FATIGUE` weights movement patterns by
  systemic/CNS cost. High-CNS compounds (hinge, vertical pull, squat) get +15s rest
  (`FATIGUE_REST_BONUS`, applied before the age multiplier). A per-day fatigue score
  (`fatigue_report` + `GET /api/plans/{id}/fatigue`, shown on `/plan`) surfaces balance;
  the canonical U/L split already alternates so consecutive days aren't both peak-fatigue
  (verified in tests). Note: the 5-day PPL split has an inherent Pull→Legs adjacency the
  report makes visible (splits in §6.2 are not reordered).
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

**Comparison note (vs. wger).** A 2026-06 review of `wger`'s routine engine
(declarative per-field change-configs: `operation ∈ {+,-,replace}`, `step ∈
{absolute,percent}`, `repeat`, log-gated `requirements`, plus a `class_name`
custom-logic hook) surfaced gaps our reactive engine doesn't cover. They are
captured as future, **rule-based** roadmap items in **§19.7** rather than here,
since none is built. Key takeaways: wger is *declarative* (the user authors the
schedule; the engine only advances when logs meet a `>=` gate and never regresses),
whereas HomeShred is *reactive* (it reads logged reps + RPE and auto-decides
progress/hold/deload). Our engine is the stronger autoregulator; wger is the more
expressive scheduler. The borrowable gaps are in §19.7.

---

## 17. AI / ML Roadmap (local-first, CPU-only)

> Status: **roadmap only — nothing here is built.** The MVP (§1–§14) and the rule
> engine (§16) are intentionally ML-free. This section records *where* learning-based
> or NL features could add value and *how* to add them without breaking the project's
> two load-bearing constraints.

### 17.1 Constraints that shape every choice
1. **Privacy / self-host (SPEC §14).** The app is LAN/Tailscale-only with no public
   exposure. A cloud LLM (e.g. the Claude API) would send workout/body data off the
   host — only acceptable behind an explicit, opt-in consent toggle. **Default stance:
   keep inference local.**
2. **Target hardware: CPU-only homelab.** No GPU. This caps local LLMs at small
   (≤~4B, quantized) models and rules out heavy DL on the server. On-device (browser)
   inference on the user's phone is unconstrained by the server and is preferred where
   it fits.
3. **The rule engine stays authoritative.** Any model *proposes*; §6/§7/§16 services
   *validate*. A model must never bypass the equipment constraint (§1) or write an
   unvalidated plan/prescription.

### 17.2 Two tracks
- **Track A — Classic ML / time-series** (tabular, runs in-process, CPU, tiny).
- **Track B — Local LLM + on-device DL** (NL features via a local model; computer
  vision on the phone).

Cloud LLM is documented as a **fallback**, not the default (§17.7).

### 17.3 Track A — Classic ML & time-series (local, in-process)
- **A1 — Adaptive TDEE / calorie auto-tuning. ✅ DONE (M1).** Estimates real maintenance
  from the bodyweight **trend**: a least-squares slope over `body_metrics` (kg/day, noise-
  robust, no extra deps) feeds `estimated_TDEE = mean_intake − slope×7700`. Intake uses
  measured `food_log` kcal on logged days and falls back to the `nutrition_targets` in
  effect on unlogged days. Guardrails: ≥4 weigh-ins spanning ≥14 days in a 28-day
  window, estimate clamped to ±25% of the static TDEE. Pure `linear_slope` /
  `adaptive_estimate` (unit-tested), `GET /api/nutrition/adaptive` (preview, `enough_data`
  flag) + `POST /api/nutrition/adaptive/apply` (persists today's target), and an Adaptive
  TDEE card on `/nutrition`.
- **A2 — Per-user load / readiness prediction. ✅ DONE (M4, baseline).** A regressor
  (scikit-learn / LightGBM) over logged sets predicting next-session load or a readiness
  score from RPE + bodyweight (+ optional sleep) was the original intent, but a solo user
  is data-starved (≈3–5 sessions/week → a year+ to train usefully). **Shipped baseline:**
  `services/prediction.py` reuses the §17.3-A1 least-squares maths over each exercise's
  per-session strength signal (e1RM for weighted, top-set reps for bodyweight) from
  `exercise_strength`, projects one session ahead (`forecast_next`), and tempers the
  verdict with recent RPE (`readiness_from`: progress / hold / insufficient). Guardrails:
  `MIN_SESSIONS_FOR_PREDICTION = 4`, a heuristic `confidence_for(n)`. No new deps.
  `GET /api/progress/prediction`; a "Next-session forecast" card on `/progress`
  (`lib/prediction.ts`). **Swap path:** replace `forecast_next` with a trained regressor
  once a year of history exists — the API/FE are unchanged. Pure helpers unit-tested.
- **A3 — Local semantic exercise search. ✅ DONE (M4, lexical baseline).** Embeddings
  (`all-MiniLM-L6`, ~80 MB via ONNX Runtime / `fastembed`) are the target, but to ship
  today with zero model downloads on the CPU-only host, `services/exercise_search.py`
  is a dependency-free **lexical ranker**: weighted token overlap across
  name / muscles / pattern / category plus a small domain `SYNONYMS` map (so "rdl" →
  romanian deadlift / hinge / hamstring). `GET /api/exercises/search?q=`; a search box
  on `/exercises`. **Swap path:** a true embedding backend drops in behind the same
  `rank_exercises` interface. Pure helpers (`tokenize`/`expand`/`score_doc`/
  `rank_exercises`) unit-tested.

### 17.4 Track B1 — Local LLM (Ollama sidecar)
Run an open model on the homelab box; the backend talks to it over the internal Docker
network (same pattern as backend↔db). Zero data leaves the host.
- **Deployment:** add an `ollama` service to `docker-compose.prod.yml`; backend reads
  `OLLAMA_URL=http://ollama:11434`.
- **Models (CPU-only):** Llama 3.2 3B, Qwen 2.5 3B, Phi-3.5-mini, Gemma 2 2B —
  quantized GGUF (Q4), ~2–4 GB RAM, a few seconds/response on CPU.
- **Structured output:** Ollama `format: "json"` (or llama.cpp GBNF grammar) → the
  model returns a schema-valid object that a rule-engine service validates before
  anything is persisted.
- **Realistic scope on CPU/≤4B:** good enough for *parsing/extraction*; weak at nuanced
  coaching prose.
  - **B1a — NL food logging:** "2 eggs and oatmeal" → grams P/C/F, logged against
    targets. Best first LLM slice (high daily utility, low risk).
  - **B1b — Exercise substitution:** "my shoulder hurts, swap overhead press" → the
    model suggests a replacement; the generator's equipment/pattern/level rules confirm
    it's valid before swapping.
  - **B1c — Plan/why explanations:** acceptable but quality-limited on a 3B model;
    revisit if hardware improves or via the cloud fallback (§17.7).

### 17.5 Track B2 — On-device DL (browser, the most private option)
Runs in the browser **on the user's phone** — video never reaches the server, so it's
unconstrained by the CPU-only host and the strongest privacy story.
- **B2a — Pose-based rep counting + form/ROM check. ✅ DONE (M3).** MediaPipe Pose
  (Tasks Vision, `pose_landmarker_lite`) loaded from a CDN **at runtime** (kept out of
  the bundle so the build needs no model and the CPU-only host never touches video),
  wired into `/workout/[planDayId]` per set. Pure, unit-tested core: `lib/pose.ts`
  (joint-angle geometry + per-pattern `PATTERN_TRACK` joint/threshold config) and
  `lib/rep-counter.ts` (a hysteresis state machine that counts on the contraction→lockout
  transition and flags partial ROM against `targetBottom`). `components/pose-rep-counter.tsx`
  runs the webcam loop and feeds counted reps into the set's rep field. Single-joint
  movements only (squat/hinge/push/pull); core & conditioning are untracked. Degrades
  gracefully when the camera/model is unavailable.
- **B2b — Food logging without a vision model. ✅ DONE (M4, lookup).** **Barcode
  scanning** via the browser-native `BarcodeDetector` API (no ML, no extra deps;
  `components/barcode-scanner.tsx`, manual digit-entry fallback) + an **Open Food Facts**
  lookup: `services/food_lookup.py` (`parse_off_product` pure/unit-tested mapper,
  `lookup_barcode` httpx fetch), `GET /api/nutrition/barcode/{code}`. Returns per-100 g
  macros scaled to a serving on the FE (`lib/food.ts`) and can now be explicitly saved
  into the daily `food_log` (§19.1). **Note:** an OFF lookup leaves the LAN, so it is opt-in /
  external (§17.7); an offline OFF dump can replace `lookup_barcode` behind the same
  interface for a fully local path.

### 17.6 Recommended phasing
- **M1 — A1 Adaptive TDEE. ✅ DONE.** (light, local, uses existing data, immediate value).
- **M2 — B1 Ollama sidecar** → B1a food logging, then B1b substitution (rule-validated).
  **Still pending** — the only AI/ML milestone not yet built.
- **M3 — B2a pose rep-counting / form check. ✅ DONE** (browser, fully on-device).
- **M4 — A2 prediction model + A3 search + B2b barcode. ✅ DONE** as baselines (A2 is a
  trend baseline pending a year of data for a trained regressor; A3 is lexical pending
  embeddings; B2b is lookup pending a food-log table).
Each milestone ships behind a feature flag; any feature that leaves the LAN ships behind
an explicit opt-in consent toggle.

### 17.7 Cloud LLM — explicit fallback, not the default
If local quality proves insufficient for coaching/conversational plan edits, a
hosted model (e.g. the Claude API — Haiku for cheap parsing, Sonnet/Opus for coaching)
is the higher-quality option. It is **opt-in only**, sends the minimum necessary data,
and still routes every proposed change through the rule engine. Keeping the assistant
behind one `assistant.py` service interface means local vs cloud is a config switch, not
a rewrite.

---

## 18. Analytics — Personal Records & Strength Trend (`services/strength.py`)

Turns the existing `set_logs` into the "am I getting stronger?" view the app otherwise
lacks. Pure read/aggregation over completed sessions — **no new tables, no rule-engine
change**.

### 18.1 Estimated 1RM
`e1RM = weight_kg × (1 + reps / 30)` (Epley), rounded to 0.1 kg. Bodyweight sets
(`weight_kg` null) have no e1RM — their strength signal is **top-set reps** instead. The
same formula is used on the FE history recap (`lib/exercise-history.ts`) — keep them in
sync.

### 18.2 What is computed (per exercise, completed sessions only)
- **PRs**: `best_e1rm` (max session e1RM), `best_weight` (heaviest single set),
  `best_reps` (most reps in a single set — the bodyweight strength signal).
- **Trend series**: one point per session, chronological:
  `{date, e1rm | null, top_weight | null, top_reps}` where `e1rm`/`top_weight` are the
  best of that session. The FE plots `e1rm` for weighted exercises, `top_reps` for
  bodyweight ones.
- **`latest_is_pr`**: the most recent session set a new all-time best (by e1RM for
  weighted exercises, by reps for bodyweight). Drives a 🏆 badge on the progress page.

Exercises with no completed sets are omitted; the list is ordered by most-recently-trained.

### 18.3 Endpoint
`GET /api/progress/strength → list[ExerciseStrengthOut]`
(`ExerciseStrengthOut{ exercise_id, exercise_name, pattern, weighted, best_e1rm,
best_weight, best_reps, latest_is_pr, points: list[StrengthPointOut] }`).

### 18.4 Boundary (deliberate)
PR celebration lives on **`/progress`**, computed server-side over full history. It is
**not** wired into the in-runner session summary: the runner only fetches the last few
sessions per exercise (§16 follow-up), so it cannot reliably detect an all-time PR
without a second full-history fetch. Revisit if a dedicated "session PRs" endpoint is
added.

### 18.5 Tests (mandatory)
- `epley_1rm` formula + bodyweight (null) → None.
- `exercise_strength`: PRs correct; trend chronological; `latest_is_pr` true only when the
  last session is a new best (weighted by e1RM, bodyweight by reps); incomplete sessions
  excluded; empty → `[]`.
- FE `lib/strength.ts`: chart-series selection (e1RM vs reps) + PR-label formatting.

---

## 19. What's Next — Roadmap & Brainstorm

> State as of this revision: MVP + §16 (R1–R7) + §17 M1/M3/M4 + §18 + the §19.1
> food log (+ quick-add recent, copy-day, and nutrition history/adherence, §19.5) +
> named profile manager all shipped.
> 130 backend tests, 72 FE tests;
> ruff/eslint clean, build green. The single remaining AI/ML milestone is **M2
> (Ollama sidecar)**. Below is the recommended ordering, grounded in what each item
> unblocks rather than novelty.

### 19.1 Food log. ✅ DONE
The keystone nutrition gap is now closed:
- `food_log` table (`id, date, name, grams, kcal, protein_g, carbs_g, fat_g,
  source enum{manual,barcode,llm}, barcode?, created_at`).
- `services/food_log.py` computes daily entries, totals, remaining-vs-target, and the
  adaptive-TDEE intake series.
- `GET/POST/DELETE /api/nutrition/log`; `/nutrition` has a daily food-log card, manual
  add form, delete actions, and barcode lookup → "Add to log".
- §17.3 A1 now uses **measured intake** on logged days and falls back to the target proxy
  otherwise. This preserves old behavior when the user does not log food.

### 19.2 M2 — Ollama sidecar (the last AI/ML milestone)
- Add an `ollama` service to `docker-compose.prod.yml`; backend reads `OLLAMA_URL`.
- One `services/assistant.py` interface so local-vs-cloud (§17.7) is a config switch.
- **B1a NL food logging** ("2 eggs and oatmeal" → grams P/C/F) using Ollama
  `format:"json"`, validated against a Pydantic schema before writing to the §19.1
  food log. Highest daily utility, lowest risk — build it first.
- **B1b LLM substitution** ("shoulder hurts, swap overhead press") → suggestion is
  re-validated by the existing equipment/pattern/level generator rules before swapping.
- Ships behind a feature flag; degrade to the current rule-only behaviour if the
  sidecar is down.

### 19.3 Maturing the M4 baselines (once data justifies it)
- **A2 → trained regressor.** Keep logging RPE/sleep/bodyweight; once ~6–12 months of
  history exists, replace `forecast_next` with scikit-learn/LightGBM behind the same
  interface. Add an optional **sleep** input to readiness/A2 (currently energy/soreness/
  sleep are runner-only and not persisted — persist them to feed the model).
- **A3 → embeddings.** Swap the lexical ranker for `all-MiniLM-L6` via `fastembed`/ONNX
  behind `rank_exercises` if lexical recall proves insufficient in practice.
- **Pose (B2a) follow-ups.** Auto-log a set when the camera detects the target rep
  count; persist a per-set form/ROM score (needs a `set_logs.form_score` column);
  extend beyond single-joint movements; add tempo/eccentric-time cues.

### 19.4 Product gaps independent of AI/ML
- **Operations (SPEC §14.7):** `pg_dump` backup cron; set a strong prod DB password
  (still the example placeholder); finish the real-host deploy (port 3000 free there).
- **Phone-in-the-gym polish:** PWA manifest + service worker for offline set logging
  and "add to home screen"; the runner is the one screen that must work with flaky gym
  wifi.
- **Plan lifecycle:** a "deload week" / mesocycle-rollover prompt; archiving old plans;
  editing a generated plan (swap/reorder before starting).
- **Light auth:** a single shared passcode or reverse-proxy basic-auth for the LAN —
  currently anyone on the network can hit the API (acceptable for now, flagged here).
- **Data ownership / export:** a one-click JSON/CSV export of workouts, set logs, body
  metrics, nutrition targets, and the food log (and an import to match) — a self-host
  user should be able to take their data with them. Complements the §14.7 `pg_dump`
  cron but is user-facing (no shell access needed) and pure read/serialisation, so no
  schema change.
- **Profile-scoped history (only if needed):** named profiles currently behave as saved
  active presets inside a solo app; plans, sessions, body metrics, nutrition targets,
  and food logs are global. If the app becomes family/multi-person in practice, add
  `profile_id` to those tables and migrate existing rows to the active profile. Until
  then, keep this out of scope to avoid turning a solo app into multi-user software.

### 19.5 Nutrition follow-ups (now unblocked by the food log)
The §19.1 `food_log` table makes several high-utility, rules-only nutrition features cheap
to add — no ML, no new external calls. Highest daily value first:
- **Quick-add / recent foods.** ✅ DONE. `GET /api/nutrition/log/recent?limit` returns the
  most-recent *distinct* foods (distinctness keys on name+macros+barcode so different
  serving sizes stay separate); `/nutrition` renders them as one-tap chips that re-log via
  the existing `FoodLogIn` path (`recentFoodToLog`). A persisted `favorite` flag is still a
  possible follow-on but recency alone covers the daily-friction case.
- **Copy a day.** ✅ DONE. `POST /api/nutrition/log/copy-day {from_date, to_date}` clones
  every entry from a source day into the selected day (404 if the source day is empty);
  `/nutrition` has a "Copy a day" control defaulting to the day before.
- **Nutrition history & adherence.** ✅ DONE. `GET /api/nutrition/log/history?end_date&days`
  returns daily logged kcal/macros plus the target in effect for each day. `/nutrition`
  shows a 7-day adherence card with kcal-vs-target bars, macro trend lines, and daily
  status chips. A day counts as adherent when food was logged and calories land within
  90–110% of that day's target.
- **Meal / recipe templates.** Save a named combination of foods (e.g. "post-workout
  shake") and log it as one entry — natural follow-on once quick-add exists.

These also de-risk **M2 B1a** (§19.2): NL food logging just needs to emit the same
`FoodLogIn` shape the manual/quick-add paths already validate.

### 19.6 Suggested order
1. **Ops hardening** (backups, password, deploy) — do before relying on it daily.
2. **Nutrition follow-ups** (§19.5) — quick-add/copy-day/history ✅ done; next is
   meal/recipe templates. Cheapest remaining wins.
3. **PWA/offline** for the runner.
4. **Data export/import** (§19.4) — once there's enough data worth owning.
5. **Plan lifecycle** (archive/edit plans, mesocycle rollover prompt).
6. **Profile-scoped history** (§19.4) — only if the named-profile manager starts being
   used as real multi-person support.
7. **A2/A3/pose maturation** — only when accumulated data makes the upgrade pay off.
8. **M2 B1a/B1b** remains available later, but is intentionally ignored for now.

### 19.7 Progression-engine gaps (vs. wger) — rule-based, not yet built
A review of `wger`'s routine progression engine (declarative per-field
change-configs, log-gated requirements, `class_name` custom hook) against our §7/§16
engine identified the following borrowable, **ML-free** improvements. Our engine is
the stronger *autoregulator* (it reads logged reps + RPE and auto-decides
progress/hold/deload, deloads on a grind, and schedules a mesocycle deload — wger does
none of this natively); wger is the more expressive *scheduler*. These items close that
expressiveness gap **without** dropping our reactive defaults. Ordered by value/effort:

- **P1 — User progression overrides (per plan_exercise).** Today the engine's automatic
  decision is the only option. Add an optional per-exercise override so the user can pin
  a scheme (e.g. "+2.5 kg every week regardless", "hold reps, ramp sets") that
  `suggest_next_targets` honours ahead of the reactive rules. Mirrors wger's declarative
  change-config but keeps reactive autoregulation as the default when no override is set.
  Likely a new `plan_exercise.progression_override` JSON/enum column + a branch at the top
  of `suggest_next_targets`.
- **P2 — Per-field independent progression.** Our engine progresses weight **or** reps
  only; rest/sets are fixed at generation. wger schedules ten fields independently. Allow
  reps, weight, sets, and rest to each carry their own multi-week intent so undulating /
  block schemes are expressible. Builds on P1's override shape.
- **P3 — Authorable periodization curve.** §16 R2's 4-week curve (1.0/1.1/1.2/0.6) is
  fixed. Let the user supply a custom per-week volume/intensity curve (linear, undulating,
  block) — a small data-driven table, same spirit as `WEEK_PERIODISATION` but per-plan.
- **P4 — Custom-strategy escape hatch.** wger's `class_name` lets a routine plug in
  arbitrary progression logic. A `services/progression.py` strategy interface (a
  `Protocol` + registry) would let non-default schemes (5/3/1-style, RPE-capped linear,
  etc.) drop in behind the same `suggest_next_targets` call without forking the engine.
- **P5 — Set-type & rep-unit semantics.** wger models warmup/dropset/myo/AMRAP sets and
  reps/time/distance units; our conditioning is convention-only (§6.7). Add a set-type
  enum + rep-unit so AMRAP/time-based work is first-class (also sharpens §9 volume and the
  runner timer). Larger schema touch — lowest priority.

Note the one place **neither** engine leads: both are short-memory (we read
`recent_sessions[:2]`; wger checks only the prior iteration's logs). The true multi-week
trend upgrade is already tracked as §16 limitation #2 → §19.3 (trained regressor), not
here.

### 19.8 Feature-level gaps (vs. wger) — rule-based, not yet built
§19.7 covered the *progression engine*. A broader feature sweep of `wger` surfaced four
borrowable, **ML-free** product features that fit HomeShred's solo / local-first / phone-in-
the-gym design (gym multi-user, native mobile apps, and 40-language i18n were reviewed and
deliberately left out of scope). Ordered by value/effort:

- **W1 — Custom body measurements. ✅ DONE.** `measurement_types` (`key` unique, `label`,
  `unit`, `builtin`) + `measurement_entries` (`type_id` FK ON DELETE CASCADE, `date`, `value`;
  unique per type+day = upsert) via migration `d1e2f3a4b5c6`, with nine built-in circumference
  types seeded (chest/shoulders/hips/arms/thighs/calf/neck). weight/bf%/waist deliberately
  stay in `body_metrics` (the §8 nutrition engine reads them) and are not duplicated here.
  `services/measurements.py` (slugified keys, idempotent `ensure_builtin_types`, per-type
  `measurement_series` with latest/change); `GET/POST/DELETE /api/measurements/types`,
  `GET/POST/DELETE /api/measurements/entries`, `GET /api/measurements/series`. Built-ins
  can't be deleted (409); duplicate label = 409; entry for a missing type = 404. FE: a "Body
  measurements" card on `/progress` (latest+change tiles, per-type trend chart, log form,
  add/delete custom types) + pure `lib/measurements.ts`. Tests: `tests/test_measurements.py`
  (7) + `lib/measurements.test.ts` (4).
- **W2 — Food search by name. ✅ DONE.** Closes the gap where a food could only be added by
  barcode scan (§17.5 B2b) or manual macros. `GET /api/nutrition/food/search?q=&limit=` queries
  the OFF text-search endpoint, upserts hits into a local `foods` cache (migration
  `e2f3a4b5c6d7`; barcode-keyed, name-indexed, per-100 g macros), then returns matches **from
  the cache** — so repeat searches are offline/fast and an OFF outage degrades to cached results
  instead of erroring. `services/food_search.py` shares `food_lookup.product_to_facts`; pure
  `parse_off_search` is unit-tested without network. The endpoint returns `FoodFactsOut` so the
  FE reuses `lib/food.ts` scaling. FE: a "Search a food" card on `/nutrition` (search → pick →
  grams → Add to log, same `FoodLogIn` path as the scanner). Tests: `tests/test_food_search.py`
  (7, network monkeypatched). Note (§17.7): an OFF query leaves the LAN — opt-in/external.
- **W3 — Progress photos gallery. ✅ DONE.** `progress_photos` table (`date`, `filename`,
  `content_type`, `note`) via migration `f3a4b5c6d7e8`; image bytes are written to disk under a
  configured `MEDIA_DIR` (new setting; mounted as the `media` volume in
  `docker-compose.prod.yml`, gitignored in dev). `services/progress_photos.py` validates
  content type (JPEG/PNG/WebP → 415) and size (≤10 MB → 413), takes raw bytes (HTTP-agnostic /
  testable). Endpoints on the progress router: `POST /api/progress/photos` (multipart),
  `GET /api/progress/photos`, `GET /api/progress/photos/{id}/image` (FileResponse),
  `DELETE /api/progress/photos/{id}` (removes row + file). FE: a "Progress photos" gallery card
  on `/progress` (upload with date+note, newest-first grid, delete). Added `python-multipart`.
  Tests: `tests/test_progress_photos.py` (6, tmp media dir). Export manifest (§19.4) deferred
  with the rest of export.
- **W4 — Session impression + workout calendar.** `WorkoutSession` already has `notes` but no
  overall impression. wger logs a per-session general impression (good/neutral/bad) and shows a
  workout calendar. Add a `WorkoutSession.impression` enum column (nullable, runner captures it
  on completion) and a month calendar view on `/progress` (or a new `/calendar`) marking
  trained days + impression colour. Small; pairs with persisting the runner's energy/soreness/
  sleep inputs already noted in §19.3.

These are independent of each other and of the §19.7 P-items; W1 and W2 are the highest
value-per-effort. Suggested insertion into the §19.6 order: W1/W2 alongside the nutrition
follow-ups (cheap, high daily value), W4 with plan-lifecycle/PWA polish, W3 once media storage
is worth operating.
