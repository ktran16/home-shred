# HomeShred — Frontend

Next.js 16 (App Router, Turbopack) + TypeScript (strict) + Tailwind. Mobile-first;
server state via TanStack Query; typed API client generated from the backend OpenAPI.

## How to run (dev)

```bash
pnpm install
pnpm dev          # http://localhost:3000
```

`/api/*` is proxied to the backend (`BACKEND_INTERNAL_URL`, default
`http://localhost:8000`) via `next.config.ts` — so the browser only talks to the
FE origin (no CORS). Start the backend first (see `../backend/README.md`).

## Generated API client

The API contract is the backend OpenAPI schema. Regenerate types whenever the
backend API changes:

```bash
# from backend/: dump the schema
uv run python -c "import json; from app.main import app; open('../frontend/openapi.json','w').write(json.dumps(app.openapi()))"
# from frontend/: regenerate types
pnpm gen:api
```

- `lib/api.d.ts` — generated types (do not edit).
- `lib/api.ts` — `openapi-fetch` client (relative baseUrl).

## Lint / build

```bash
pnpm exec eslint .
pnpm build
```
