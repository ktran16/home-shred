# HomeShred — Docker Compose helpers.
#   DEV  (docker-compose.yml):      postgres (host :5434) + adminer (host :8080).
#                                   backend/frontend run on the host (uv run / pnpm dev).
#   PROD (docker-compose.prod.yml): db + backend + frontend (host :3006), reads .env.prod.
#
# Run `make help` for the full target list.

DC          := docker compose
DEV         := $(DC) -f docker-compose.yml
PROD        := $(DC) -f docker-compose.prod.yml
SEED        := python -m app.seed.seed_exercises

.DEFAULT_GOAL := help

.PHONY: help \
        up down logs ps restart adminer \
        prod-up prod-down prod-logs prod-ps prod-restart prod-build \
        prod-seed prod-reset prod-shell prod-psql prod-health

## ----------------------------------------------------------------------------
## Meta
## ----------------------------------------------------------------------------

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## ----------------------------------------------------------------------------
## Dev — Postgres + Adminer only (backend/frontend run on host)
## ----------------------------------------------------------------------------

up: ## Start dev db + adminer
	$(DEV) up -d

down: ## Stop dev stack (keeps data)
	$(DEV) down

logs: ## Tail dev logs
	$(DEV) logs -f

ps: ## Show dev container status
	$(DEV) ps

restart: ## Restart dev stack
	$(DEV) restart

adminer: ## Print the Adminer URL
	@echo "Adminer: http://localhost:8080  (server: db, user: homeshred, db: homeshred)"

## ----------------------------------------------------------------------------
## Prod — full stack (db + backend + frontend on :3006), reads .env.prod
## ----------------------------------------------------------------------------

prod-up: ## Build + start the prod stack (detached)
	$(PROD) up -d --build

prod-build: ## Rebuild prod images without starting
	$(PROD) build

prod-down: ## Stop the prod stack (keeps data)
	$(PROD) down

prod-logs: ## Tail prod logs (override: make prod-logs S=backend)
	$(PROD) logs -f $(S)

prod-ps: ## Show prod container status
	$(PROD) ps

prod-restart: ## Restart the prod stack
	$(PROD) restart

prod-seed: ## Seed the 54 exercises into the prod db
	$(PROD) run --rm backend $(SEED)

prod-shell: ## Open a shell in the backend container
	$(PROD) exec backend sh

prod-psql: ## Open psql in the prod db
	$(PROD) exec db psql -U homeshred -d homeshred

prod-health: ## Curl the public frontend + /api/health on :3006
	@echo -n "FE:        "; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3006
	@echo -n "API health: "; curl -s http://localhost:3006/api/health; echo

# WARNING: drops the pgdata volume (erases the DB), then rebuilds + re-seeds.
# Required after any DB password change — Postgres only applies POSTGRES_PASSWORD
# on the FIRST init of an empty data dir (see HANDOFF.md "Deploy fix").
prod-reset: ## DESTRUCTIVE: drop db volume, rebuild, re-seed
	$(PROD) down -v
	$(PROD) up -d --build
	$(PROD) run --rm backend $(SEED)
	@$(MAKE) prod-health
