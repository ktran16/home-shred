# CLAUDE.md — Coding Conventions for HomeShred

> Read `SPEC.md` first for *what* to build. This file is *how* to build it.
> Apply these on every file you touch. When in doubt, match existing patterns in the repo.

## Workflow
- Build strictly phase-by-phase per `SPEC.md §12`. Do not start a phase until the previous one runs and its tests pass.
- One commit per logical unit; conventional-commit style: `feat(plan): add split templates`, `fix(api): 409 when no profile`.
- After each phase: update `README.md` (how to run), run `ruff check` + `ruff format`, run `pytest`. Zero lint errors before moving on.
- Never edit an applied Alembic migration — create a new one.

## Backend (Python)
- Target Python 3.12+. Manage deps with `uv` only. Local `.venv`. Never use pip/conda.
- **Type-annotate everything.** Run `ruff` (lint + format); fix all warnings.
- SQLAlchemy 2.0 modern style: `Mapped[...]` + `mapped_column(...)`, fully async (`AsyncSession`). Sessions via FastAPI dependency `get_db`.
- Keep ORM models (`app/models`) and Pydantic schemas (`app/schemas`) **separate**. Never return ORM objects directly — map to schemas.
- Pydantic v2: `model_config = ConfigDict(from_attributes=True)` on response schemas.
- **Business logic lives in `app/services`, not in routers.** Routers only: parse request → call service → return schema. Services are pure-ish and unit-testable without HTTP.
- Config via `pydantic-settings` reading `.env`. Provide `.env.example`. No secrets in code.
- Tunable rules (splits, prescriptions, factors) → module-level dicts/constants at top of file, each with a `# rationale:` comment linking to the SPEC section.
- Use `enum.StrEnum` for all enums (see `SPEC §4`); store as text in DB.
- Errors: raise `HTTPException` from routers with correct status (404/409/422). Services raise domain exceptions that routers translate.

## Testing (backend)
- `pytest` + `pytest-asyncio`. Use a transactional test DB (separate schema or testcontainers); never the dev DB.
- Every service module has a matching `tests/test_<module>.py`.
- The §6.9 plan-generator tests and the §7 progression tests are **mandatory gates** — the equipment-constraint test failing means the feature is not done.
- Prefer deterministic tests: seed RNG; assert on structure and ranges, not on a specific exercise name.

## Frontend (TypeScript / Next.js)
- TypeScript `strict: true`. No `any` — use generated API types.
- Generate the API client from the backend OpenAPI schema (`openapi-typescript` → types, `openapi-fetch` → client in `lib/api.ts`). Re-generate when the backend API changes; never hand-write request/response types.
- Server state via TanStack Query. No Redux/Zustand unless a real need appears.
- Components: shadcn/ui primitives + Tailwind. Mobile-first; design for a phone held in the gym. Big tap targets (min 44px), sticky bottom bars for the timer.
- **No HTML `<form>` submit semantics that reload the page** — use `onClick`/`onChange` handlers.
- Keep components small; colocate route-specific components under the route folder, shared ones in `components/`.
- Format with prettier; lint with eslint (next config). Zero errors before commit.

## API contract discipline
- The FastAPI OpenAPI schema is the contract. FE consumes generated types. If you change a schema, regenerate the FE client in the same commit.
- Dates: API uses ISO `date`/`datetime` strings; store UTC in DB.

## General
- Prefer the simplest correct solution. Leave `# TODO(spec)` where the spec is ambiguous rather than inventing scope.
- No premature abstraction; this is a solo app. Don't add auth, multi-tenancy, caching layers, or message queues unless `SPEC.md` asks.
- Write a one-paragraph "how to run" per service in `README.md` and keep it current.
